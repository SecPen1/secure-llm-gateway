# Secure LLM Gateway

A reference implementation of a security-focused gateway sitting in front of an LLM API (Claude), built as a portfolio project demonstrating applied security architecture — not just working code, but the design decisions and trade-offs behind it.

**Status:** v1 complete — all 6 slices done. See the docs below for the design work behind it.

## Why this exists

This project is a hands-on demonstration of security architecture thinking applied to a real, if small, system: an LLM gateway that mediates access between client applications and an upstream LLM API. It's built slice-by-slice, with each control mapped back to a specific entry in the threat model and documented as it lands.

## Docs

- [THREAT_MODEL.md](THREAT_MODEL.md) — assets, actors, STRIDE-based attack paths, and trust boundaries

## Build order (v1)

1. **Input validation & sanitization** — done (see below)
2. **Auth layer (per-client, scoped)** — done (see below)
3. **Prompt injection defenses** — done (see below)
4. **Output filtering** — done (see below)
5. **Audit logging** — done (see below)
6. **Rate limiting / cost controls** — done (see below)

Each slice gets a working control, a README section explaining the design decision behind it, and a test or demo showing it functioning.

## Getting started

```bash
python -m venv .venv
.venv\Scripts\activate      # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# run the gateway
uvicorn gateway.main:app --reload

# run the tests
pytest

# register a client and get an API key (printed once)
python scripts/generate_client_key.py my-client

# verify the audit log's tamper-evident hash chain
python scripts/verify_audit_log.py
```

Note: the default rate limit (5 requests, refilling at 1 per 2 seconds per client) applies immediately — expect `429`s if you script more than a handful of quick requests against one client while testing.

## Local demo UI

Once the gateway is running (`uvicorn gateway.main:app --reload`), open **http://127.0.0.1:8000/** in a browser. It's a single static page (`gateway/static/index.html`, no build step, no framework) served by the gateway itself, that talks to `POST /v1/chat` exactly like any other client — nothing about the demo is special-cased in the backend.

Paste in a Client ID and API key (generate one with `scripts/generate_client_key.py` — the page has a reminder), then either type your own message or click a preset to see a specific control fire: a benign message passing straight through, a prompt-injection attempt getting blocked with its matched categories shown, a credit card number coming back redacted, a client-submitted `role: "system"` message getting rejected, or firing six requests back-to-back to watch the rate limiter kick in mid-flood. The response panel shows the exact JSON the gateway returned, so nothing is hidden between the click and the control.

This is local-only by design — not deployed or publicly hosted. Standing it up somewhere public would mean running the backend continuously (cost, uptime, another thing that can break), which wasn't worth it for a repo whose primary audience reads code and design docs; running it locally in under a minute is enough to make every control tangible without that ongoing maintenance surface.

## Slice 1: Input validation & sanitization

**What it does:** every request to `POST /v1/chat` is checked against a strict schema (`gateway/schemas.py`) before anything else happens — required fields, allowed roles, and length limits on both the message list and each message's content. Requests that fail schema validation are rejected with `422` before they reach any application logic.

On top of schema validation, each message's content was originally screened against a small, flat list of known prompt-injection phrasings. That screening has since been superseded by the layered defense built in slice 3 (`gateway/injection_defense.py`) — see below.

**Design decision — why heuristics now, not a classifier:** this heuristic screening is a coarse first gate at the input boundary, not the full prompt-injection defense. Starting with a small, explainable regex list keeps this slice honest about what it actually catches — a determined attacker can phrase around a fixed pattern list — while giving a cheap, auditable layer to build on. Committing to a trained classifier in slice 1 would be building ahead of scope per the project's build order.

**Maps to threat model:** `THREAT_MODEL.md` → Tampering (strict input schema validation) and Information Disclosure (early-stage injection screening).

**Demo:** see `tests/test_input_validation.py` — covers a valid request, a missing field, an oversized message, an invalid role, and a blocked injection attempt.

## Slice 2: Auth layer

**What it does:** `POST /v1/chat` now requires `Authorization: Bearer <api-key>`. Keys are generated per client with `scripts/generate_client_key.py`, which prints the plaintext key once and stores only its SHA-256 hash in a local client registry (`gateway/clients.json`, git-ignored — not committed, since it's a credential store even though it holds hashes rather than plaintext). A request with no key or an unrecognized key is rejected with `401`.

Authentication runs *before* schema validation, not after — an unauthenticated caller gets a `401` without learning anything about the expected request shape.

Beyond just proving *a* valid key, the gateway checks that the authenticated client's identity matches the `client_id` in the request body. A valid key for `client-a` cannot submit a request claiming to be `client-b` — that's rejected with `403`. This closes an impersonation gap that schema validation alone can't catch.

**Design decision — why static hashed API keys, not JWT/OAuth:** for a single-hop, machine-to-machine gateway, a static per-client key is the simplest mechanism that still lets each client be authenticated, revoked, and rotated independently — and it's easy for a reviewer to read end-to-end in one file (`gateway/auth.py`). JWT/OAuth would add real value once there's a token-issuing authority or delegated third-party access to model, but for v1 that's complexity without a corresponding requirement. Keys are hashed at rest and compared with `hmac.compare_digest` (constant-time) so a timing attack or a leaked registry file can't be used to recover or brute-force a valid key trivially.

**Known gap, deliberately out of scope for v1:** keys are long-lived and static — no expiry, no rotation enforcement, no mutual TLS or replay protection. `THREAT_MODEL.md`'s Spoofing mitigation lists short-lived tokens and replay protection as the fuller answer; this slice is the foundational identity check that a future iteration would build on top of.

**Maps to threat model:** `THREAT_MODEL.md` → Spoofing (per-client key authentication) and Elevation of Privilege (client_id binding prevents one client acting as another).

**Demo:** see `tests/test_auth.py` — covers no auth header, an invalid key, a valid key, and a spoofed `client_id`.

## Slice 3: Prompt injection defenses

**What it does:** `gateway/injection_defense.py` replaces slice 1's flat pattern list with two layers:

1. **Centralized system prompts, enforced.** A request containing any message with `role: "system"` is rejected with `400`. Only the gateway is allowed to establish a system prompt — a client can no longer smuggle one in through the message array to override it. This resolves the "centralized vs. per-client system prompts" item that had been sitting open in `THREAT_MODEL.md`.
2. **Categorized, severity-scored heuristic screening.** Patterns are grouped into categories (instruction override, role/mode manipulation, system-prompt extraction, fake delimiter injection like a message trying to inject a fake `system:` turn via a newline). Each category carries a weight; a request is blocked once matched categories' weights sum to a threshold (currently 3), not on any single match. Before matching, input is Unicode-normalized (NFKC) and stripped of zero-width characters, which defeats the common trick of splitting a flagged word with invisible characters to dodge a literal regex.

**Design decision — why scoring, not "any match blocks":** a flat pattern list (slice 1) treats a single incidental word match the same as a blatant jailbreak attempt, which is exactly how these filters generate false positives in practice. Scoring lets one weak, ambiguous signal (e.g. "developer mode" in isolation) pass through, while the same signal combined with another, or a single high-confidence signal alone (like an injected fake delimiter), still blocks. The threshold and weights are a tunable, documented knob — not a claim that this is complete. This is still explicitly heuristic/regex-based, per the build order's instruction not to build a trained classifier ahead of scope.

**Known gap, deliberately out of scope for v1:** this remains pattern-based and will miss novel phrasings outside the categories covered; it's a coarse gate, not a semantic understanding of intent. `THREAT_MODEL.md` notes revisiting this if the false-negative rate proves too high in practice.

**Maps to threat model:** `THREAT_MODEL.md` → Information Disclosure (prompt injection / system-prompt extraction) and both resolved Open Design Decisions.

**Demo:** see `tests/test_injection_defense.py` — covers a benign message with incidental keyword overlap, a single weak signal that's allowed through, combined weak signals that block, a high-severity signal that blocks alone, a zero-width-obfuscated bypass attempt that's still caught, and a rejected client-submitted `role: "system"` message.

## Slice 4: Output filtering

**What it does:** before a response reaches the client, `gateway/output_filter.py` scans it for high-confidence credential and financial-identifier patterns — credit card numbers, US Social Security numbers, AWS access keys, and generic `sk-`-style API key tokens — and replaces each match with `[REDACTED:<category>]`. The response still comes back to the caller; only the matched substrings are masked. The endpoint's JSON now includes a `redactions` list naming which categories fired, so a caller (or, later, an audit log) can see that scrubbing happened without needing the original sensitive value.

This slice also introduces `gateway/llm_client.py`, a minimal pluggable client with a `generate()` interface. The only implementation right now is a deterministic stub that echoes the caller's own last message back — there's no real upstream LLM call yet. That's plumbing to give output filtering something to act on, not the deliverable; see the gap called out below.

**Design decision — redact, don't reject:** input validation (slices 1–3) rejects a whole request when something's wrong, because the client's intent is what's being judged. Output is different — the surrounding response is presumably fine; only a leaked fragment (a credential the model shouldn't have echoed) is the problem. Discarding an entire otherwise-useful response over one embedded token would be a worse trade than masking that token, so this layer redacts in place rather than blocking with an error. Patterns are deliberately scoped to high-confidence credential/financial formats rather than broad PII (e.g. email addresses aren't touched) to keep false positives low enough that the filter stays usable.

**Known gap, deliberately out of scope for v1:** the LLM call is a stub, not a real integration — so today this filter only ever sees whatever the caller's own input echoes back. Wiring a real upstream call wasn't on the v1 build order and isn't needed to demonstrate the control itself; regardless of where response text comes from, the filtering logic is the same. Also, like any regex/DLP approach, this is pattern-based: it will miss sensitive data in formats it doesn't recognize and can false-positive on coincidental digit sequences (e.g. a 16-digit number that isn't really a card). No structured-data (JSON/nested) redaction is implemented.

**Maps to threat model:** `THREAT_MODEL.md` → Information Disclosure (data exfiltration via output), covering the "LLM responses" and "API credentials" assets.

**Demo:** see `tests/test_output_filtering.py` — covers a credit card, an SSN, an AWS access key, a generic API key token, and a benign response with no redactions.

## Slice 5: Audit logging

**What it does:** `gateway/audit_log.py` writes a structured JSON-lines record for every security-relevant event: a successful chat, an auth failure, a `client_id` mismatch, a rejected client-submitted system-role message, a blocked injection attempt, and a schema-validation failure. Each record carries a timestamp, the authenticated `client_id` (or `null` where there isn't one — see below), an `event_type`, an `outcome` (`allowed`/`blocked`), and a `detail` object.

Each record also carries `prev_hash` (the previous record's hash) and its own `hash`, computed over everything else in the record. That chains every entry to the one before it — editing, reordering, or forging any past entry breaks the hash chain from that point forward. `scripts/verify_audit_log.py` walks the file and reports whether the chain is intact; `tests/test_audit_log.py` proves this concretely by tampering with a written entry and confirming verification then fails.

**Design decision — what never goes in `detail`:** no raw message content, no credentials, no redacted values — only counts, category names, and booleans (e.g. `{"categories": ["instruction_override"], "score": 4}`, never the message text that triggered it). `THREAT_MODEL.md` names the audit log itself a trusted sink that "must not contain raw secrets or excessive PII" — logging the exact content the rest of the gateway exists to screen or redact would just relocate the exposure, not close it.

**Design decision — why auth failures log `client_id: null`, not the claimed one:** at the point a key fails to validate, the only `client_id` available is whatever the caller put in the request body — unverified and attacker-controlled. Logging it as if it were real would let anyone submit a failed request claiming to be a legitimate client, planting that name into the audit trail for a failure that wasn't theirs. Nothing is logged as a client's action until that client has actually authenticated.

**Design decision — hash chain, not a real WORM store:** "immutable" for a v1 reference build without standing up infrastructure means tamper-*evident*, not tamper-*proof*. A hash chain over an append-only local file lets anyone re-derive whether stored entries have been altered — it does not stop someone with filesystem access from deleting the whole file or truncating the end of it (there's no external witness of the latest hash). `THREAT_MODEL.md`'s "Gateway → Logging/SIEM" trust boundary is the honest answer to that gap: a production deployment ships these records to a remote, access-controlled sink as they're written, rather than trusting local storage at all.

**Maps to threat model:** `THREAT_MODEL.md` → Repudiation (immutable, timestamped, identity-tied audit logging) and the "Audit logs" asset.

**Demo:** see `tests/test_audit_log.py` — covers a successful chat being logged, an injection block logged with categories but not the triggering text, an auth failure logged with no claimed identity, a redaction event logged without the raw sensitive value, and a hash-chain tamper attempt being detected.

## Slice 6: Rate limiting / cost controls

**What it does:** `gateway/rate_limiter.py` adds two independent per-client checks, both running before any content inspection (system-role rejection, injection screening) so capacity is protected before spending compute on a request that's already going to be throttled:

1. **Request-rate limiting** — a token bucket per `client_id` (default: burst up to 5 requests, refilling at 1 every 2 seconds). Allows a real conversation's natural bursts while still bounding sustained volume.
2. **Cost budget** — a rolling per-client budget (default: 20,000 cost units per 24 hours). Since there's no real upstream LLM call yet (`gateway/llm_client.py` is still a stub — see Slice 4), actual token counts aren't available; character count of submitted content is used as a documented stand-in.

Both are enforced with `429 Too Many Requests` and a `Retry-After` header. Every successful chat now also logs its `estimated_cost` in the audit trail (Slice 5), so a client's cumulative usage can be reconstructed from the log without a separate tracking system.

**Design decision — token bucket, not a fixed window counter:** a fixed window (e.g. "5 requests per minute, resetting on the minute") either double-allows a burst that straddles the window boundary or unnecessarily throttles a client sending a few messages in quick succession. A token bucket bounds the sustained rate just as strictly while tolerating legitimate bursts — the standard mainstream choice, not a novel one.

**Design decision — two separate checks, not one:** a fast burst of small requests and a slow trickle of enormous ones are different failure modes (`THREAT_MODEL.md` names both: high-volume *and* high-cost requests under Denial of Service / Denial of Wallet). Rate limiting alone wouldn't catch a client sending one request every few seconds that's each enormous; a cost budget alone wouldn't catch a rapid-fire flood of tiny ones. Composing two small, single-purpose checks stayed simpler than one mechanism trying to model both.

**Known gap, deliberately out of scope for v1:** state is in-memory, per-process — quotas reset on restart and don't hold up across multiple instances behind a load balancer; a real deployment needs a shared store (e.g. Redis) for this to be correct at scale. The cost proxy (character count) is a stand-in that should be replaced with real token usage once a real upstream LLM call exists. Anomaly detection on usage spikes (`THREAT_MODEL.md`'s fuller mitigation) is explicitly out of scope for v1.

**Maps to threat model:** `THREAT_MODEL.md` → Denial of Service / Denial of Wallet, covering the "Rate limit / usage data" asset.

**Demo:** see `tests/test_rate_limiting.py` — covers requests within capacity, a burst exceeding capacity being rejected, recovery after the refill window (using a fake clock, not a real sleep), a cost budget being exceeded, and the budget resetting after its window.

This closes out v1 scope as originally planned — stop after step 6. No further work is currently planned for this repo; it stands as the finished v1 reference build.

## Built with Claude Code

Implementation built in collaboration with [Claude Code](https://claude.com/claude-code), under my direction — I own the threat model, the design decisions, and the trade-offs documented in this repo; Claude handles scaffolding and code generation against that direction. See [CLAUDE.md](CLAUDE.md) for the working conventions used.

## License

[MIT](LICENSE)
