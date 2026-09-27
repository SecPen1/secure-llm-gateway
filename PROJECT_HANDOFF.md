# Project Handoff: Secure LLM Gateway

## Purpose

This is a portfolio project, not a production system. The goal is to build a working, well-documented reference implementation of a secure gateway sitting in front of an LLM API (Claude), suitable for:

1. Publishing publicly on GitHub as part of a job search portfolio (target roles: security architecture and security management/leadership)
2. Demonstrating applied security architecture thinking — not just code, but documented design decisions and trade-offs
3. Hands-on practice building with Claude Code

The audience for the final repo is hiring managers and architects reviewing candidates — the README and design docs matter as much as the code.

## Working Style / Priorities

- **Slice-by-slice, not big-bang.** Build one working control end-to-end before adding the next. Each slice should be independently demoable.
- **Design docs are first-class output.** Every major control should be explainable in the README: what it does, why it was built that way, what was traded off.
- **Favor clarity over cleverness.** Code should be readable by a reviewer skimming the repo, not just functional.
- **No real secrets or proprietary patterns.** This is public. Do not reference or reproduce anything from Ryan's actual employer's environment, tooling, or architecture — generic, defensible design only.

## Reference

See `THREAT_MODEL.md` in this repo for the full threat model (assets, actors, STRIDE-based attack paths, trust boundaries). All controls built should map back to a specific item in that document.

## Build Order (v1 scope) — complete

1. **Input validation & sanitization** — done. Schema validation on incoming requests, basic injection-pattern screening.
2. **Auth layer** — done. API key or token-based client authentication, scoped per client.
3. **Prompt injection defenses** — done. Heuristic detection layer (see "Open Design Decisions" in threat model — both resolved).
4. **Output filtering** — done. Scans LLM responses for sensitive-data patterns before returning to client.
5. **Audit logging** — done. Structured, hash-chained (tamper-evident) logs of requests/responses/security events.
6. **Rate limiting / cost controls** — done. Per-client quotas (token bucket) and usage tracking (cost budget).

v1 stopped after step 6, as planned. Multi-tenant network segmentation, a trained injection classifier, and advanced anomaly detection remain explicitly out of scope — see README per-slice write-ups for what each control does and doesn't cover.

## Tech Preferences

- Python 3.12 + FastAPI (decided) — Pydantic gives schema validation for free, which slice 1 leans on directly
- Avoid heavy infrastructure dependencies (no requirement for Kubernetes, service mesh, etc.) — this should run locally with minimal setup for anyone cloning the repo

## Definition of Done (per slice)

- Working code for the control
- A short section added to the README explaining the control and the design decision behind it
- Any relevant test or demo showing the control functioning (e.g. a sample malicious input being blocked)

## Not Yet Decided

- Whether to expand into a second lab project (e.g. AI agent sandboxing) after this one is complete

## Decided

- Repo name: `secure-llm-gateway` (public, under github.com/SecPen1)
- Stack: Python 3.12 + FastAPI
- Demo UI: built, local-only. A static page (`gateway/static/index.html`) served by the gateway itself — no separate hosting, no build step. Public hosting was considered and deliberately skipped: it would mean running the backend continuously for a repo whose primary audience reads code and design docs, and wasn't worth the added cost/uptime/maintenance surface.
