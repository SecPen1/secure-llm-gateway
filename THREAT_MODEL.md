# Threat Model: Secure LLM Gateway

## Overview

This document defines the threat model for a gateway service that mediates access between client applications and a large language model (LLM) API (e.g. Claude). The gateway is designed for enterprise use cases where multiple internal or external clients need controlled, auditable access to LLM capabilities.

## Assets

| Asset | Description | Sensitivity |
|---|---|---|
| System/developer prompts | Prompt templates and instructions defining gateway behavior | High — leakage enables prompt injection / jailbreak crafting |
| User inputs | Prompts submitted by end users | Medium — may contain PII or confidential business data |
| LLM responses | Generated output returned to clients | Medium — may leak training data artifacts or internal context |
| API credentials | Upstream LLM API keys, gateway auth tokens | Critical — compromise enables unrestricted, unattributed usage |
| Audit logs | Request/response metadata, security event logs | High — required for incident response and compliance |
| Rate limit / usage data | Per-client quota and cost tracking | Medium — manipulation enables denial-of-wallet attacks |

## Actors

- **Legitimate end users** — authenticated clients using the gateway as intended
- **Malicious external users** — attempt prompt injection, jailbreaks, or data exfiltration through crafted inputs
- **Compromised client applications** — a legitimate integration compromised upstream, sending malicious or excessive requests
- **Malicious insiders** — internal users with legitimate gateway access attempting to exceed authorized use
- **Automated bots/scrapers** — attempt to abuse the gateway for cost exhaustion or bulk data extraction

## Attack Paths (STRIDE-aligned)

### Spoofing
- Forged or replayed auth tokens to impersonate legitimate clients
- **Mitigation:** short-lived tokens, mutual TLS or signed request verification, replay protection (nonce/timestamp)

### Tampering
- Modification of request payloads in transit or via a compromised intermediate service
- **Mitigation:** TLS everywhere, request integrity checks, strict input schema validation

### Repudiation
- A client denies having issued a request that caused harm (data leak, cost overrun)
- **Mitigation:** immutable, timestamped audit logging tied to authenticated identity for every request/response pair

### Information Disclosure
- **Prompt injection** — malicious input manipulates the LLM into revealing system prompts or bypassing guardrails
- **Data exfiltration via output** — LLM response is crafted (via injection) to leak prior context, other users' data, or credentials embedded upstream
- **Mitigation:** input sanitization and injection-pattern detection, output filtering for sensitive-data patterns (regex/DLP-style scanning), context isolation between client sessions, least-privilege system prompts (no embedded secrets)

### Denial of Service / Denial of Wallet
- High-volume or expensive requests (long context, high token counts) drive up cost or exhaust capacity
- **Mitigation:** per-client rate limiting, token/cost budgets with hard caps, anomaly detection on usage spikes

### Elevation of Privilege
- A client with limited intended use (e.g. read-only summarization) manipulates the gateway into performing broader actions (e.g. tool use, data access) it wasn't scoped for
- **Mitigation:** per-client capability scoping, explicit allow-lists for tool/function access, no implicit trust between prompt content and system permissions

## Trust Boundaries

1. **Client → Gateway** — untrusted; all input must be validated and authenticated
2. **Gateway → LLM API** — semi-trusted; gateway must not forward unvalidated secrets or over-privileged instructions
3. **LLM API → Gateway (response)** — untrusted; treat model output as untrusted data, not as a source of instructions (never re-parse output as commands without validation)
4. **Gateway → Logging/SIEM** — trusted sink; must not contain raw secrets or excessive PII

## Out of Scope (v1)

- Model weight security / training data poisoning (upstream provider responsibility)
- Physical infrastructure security
- Multi-tenant network segmentation (assumed handled at deployment layer, noted as a v2 consideration)

## Open Design Decisions

- **Resolved (slice 3):** Heuristic/regex-based injection detection vs. a dedicated classifier model — heuristics for v1 (faster to implement, explainable). Now a categorized, severity-scored layer rather than single-pattern matching; see README Slice 3. Revisit if false-negative rate proves too high in practice.
- **Resolved (slice 3):** Centralized vs. per-client system prompts — centralized. Client-submitted messages may not use `role: system`; enforced in `gateway/injection_defense.py`. See README Slice 3.
- **Open (v2 planning):** Fail-open vs. fail-closed if the local inference backend is unreachable — see "v2 (Planned)" below. Not yet decided; must be decided before routing code is written, not after.

## v2 (Planned): Local Inference Routing

Not yet built — captured now, before implementation starts, per this project's own practice of threat-modeling a control before writing it. A second backend (local, on-machine LLM inference via Ollama) is introduced alongside the existing cloud LLM path, with a routing decision — local vs. cloud — made per-request. The existing v1 controls (auth, injection defense, output filtering, audit logging, rate limiting) are backend-agnostic and apply unchanged regardless of which backend handles a given request.

### New Assets

| Asset | Description | Sensitivity |
|---|---|---|
| Routing decision logic | The code/policy deciding whether a given request goes to the local or cloud backend | Critical — an incorrect decision here doesn't just mis-serve a request, it exports data across a confidentiality boundary that was the entire point of adding a local backend |
| Local inference endpoint | The Ollama process and its local REST API | Medium — unauthenticated by default; the gateway is the only enforcement point in front of it |

### New Attack Paths (STRIDE-aligned)

**Tampering / Information Disclosure — routing signal manipulation:** if the routing decision relies on a client-supplied signal (e.g. an explicit "not confidential" flag) rather than the gateway's own detection, a client can simply mislabel sensitive input to force it onto the cloud path. **Mitigation direction:** default routing must be driven by the gateway's own content inspection (reusing `gateway/output_filter.py`'s sensitive-data patterns against input, not just output), with any client-supplied override treated as a hint that can request the *more* restrictive (local) path but never force the *less* restrictive (cloud) one for content the gateway itself flags as sensitive.

**Information Disclosure — false-negative routing:** the same pattern-based detection limitation already documented for output filtering (misses formats it doesn't recognize) has a materially worse consequence here: a missed detection on input doesn't just skip a redaction, it sends confidential data to a third-party API that was never supposed to see it. This raises the bar on how conservatively "sensitive" should be defined for routing purposes compared to output redaction.

**New — backend-unavailability failure mode:** what happens when Ollama isn't running or is unreachable? Fail-open (silently fall back to cloud) defeats the purpose of the feature for exactly the requests it exists to protect. Fail-closed (reject the request) is safer but means a local outage becomes a hard availability failure for sensitive requests. This must be an explicit, tested decision, not an accident of whatever the HTTP client library does on a connection error. Leaning fail-closed; final call before implementation.

### New Trust Boundary

5. **Gateway → Local LLM (Ollama)** — the local inference endpoint is unauthenticated by default and typically bound to `localhost` only; the gateway remains the sole point enforcing that sensitive requests actually go there rather than to the cloud path. Unlike the existing "Gateway → LLM API" boundary (semi-trusted, external), this one is fully on-machine — but "local" is a network property, not a confidentiality guarantee by itself, if the endpoint were ever bound beyond localhost.

### Out of Scope (v2, initial pass)

- Real cloud-cost comparison — cost savings shown will be simulated against published per-token pricing initially, not measured against real API spend (avoids requiring a live billed API key for a demo feature)
- Multiple simultaneous local models / model selection policy — one local model to start
- Fine-grained per-field confidentiality tagging — binary local/cloud routing decision only for v2
