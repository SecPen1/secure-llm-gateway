# Secure LLM Gateway

A reference implementation of a security-focused gateway sitting in front of an LLM API (Claude), built as a portfolio project demonstrating applied security architecture — not just working code, but the design decisions and trade-offs behind it.

**Status:** slice 2 of 6 complete. See the docs below for the design work behind it.

## Why this exists

This project is a hands-on demonstration of security architecture thinking applied to a real, if small, system: an LLM gateway that mediates access between client applications and an upstream LLM API. It's built slice-by-slice, with each control mapped back to a specific entry in the threat model and documented as it lands.

## Docs

- [PROJECT_HANDOFF.md](PROJECT_HANDOFF.md) — project scope, working style, and build order
- [THREAT_MODEL.md](THREAT_MODEL.md) — assets, actors, STRIDE-based attack paths, and trust boundaries

## Build order (v1)

1. **Input validation & sanitization** — done (see below)
2. **Auth layer (per-client, scoped)** — done (see below)
3. Prompt injection defenses
4. Output filtering
5. Audit logging
6. Rate limiting / cost controls

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
```

## Slice 1: Input validation & sanitization

**What it does:** every request to `POST /v1/chat` is checked against a strict schema (`gateway/schemas.py`) before anything else happens — required fields, allowed roles, and length limits on both the message list and each message's content. Requests that fail schema validation are rejected with `422` before they reach any application logic.

On top of schema validation, each message's content is screened against a small set of known prompt-injection phrasings (`gateway/validation.py`) — things like "ignore previous instructions" or "reveal your system prompt." A match is rejected with `400`.

**Design decision — why heuristics now, not a classifier:** this heuristic screening is a coarse first gate at the input boundary, not the full prompt-injection defense (that's slice 3, tracked as an open design decision in `THREAT_MODEL.md` under *Information Disclosure*). Starting with a small, explainable regex list keeps this slice honest about what it actually catches — a determined attacker can phrase around a fixed pattern list — while giving a cheap, auditable layer to build on. Full injection defense will layer heuristics with more context-aware checks; committing to a trained classifier in slice 1 would be building ahead of scope per the project's build order.

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

## Built with Claude Code

This repo is built in collaboration with [Claude Code](https://claude.com/claude-code) — Claude does the implementation work, under human direction and review, for every design decision, control, and trade-off documented here. See [CLAUDE.md](CLAUDE.md) for the working conventions used.

## License

[MIT](LICENSE)
