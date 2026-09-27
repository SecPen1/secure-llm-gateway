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

- Heuristic/regex-based injection detection vs. a dedicated classifier model — starting with heuristics for v1 (faster to implement, explainable), revisit if false-negative rate is too high
- Centralized vs. per-client system prompts — leaning centralized for consistency and easier audit
