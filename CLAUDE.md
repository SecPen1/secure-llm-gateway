# CLAUDE.md

Reference doc for Claude Code sessions working in this repo. Keep this file short — put rationale and narrative in `README.md` / `THREAT_MODEL.md`, not here.

## What this is

Secure LLM Gateway — a portfolio project (see [README.md](README.md) for full scope, purpose, and audience). Public repo; audience includes hiring managers, so code and docs both need to read cleanly.

A `PROJECT_HANDOFF.md` may exist locally, git-ignored — private working notes for planning across sessions, not part of the published repo. Don't assume it exists or reference it in anything user-facing; `README.md` and `THREAT_MODEL.md` are the canonical public docs.

## Status

Python 3.12 + FastAPI. v1 complete — all 6 slices done (input validation, auth layer, prompt injection defenses, output filtering, audit logging, rate limiting / cost controls). See `gateway/`. v1's build order stopped after step 6 as planned; what's next (scope expansion, a second lab project, or leaving this as-is) hasn't been decided.

The LLM call itself is currently a deterministic stub (`gateway/llm_client.py`, `StubLLMClient`) — no real upstream API integration exists yet. Check `README.md` Slice 4 before assuming otherwise.

## Working conventions

- **Slice-by-slice**: build one control end-to-end (see Build Order in `README.md`) before starting the next. Don't build ahead of v1 scope.
- **Conventional commits**: `feat:`, `fix:`, `docs:`, `chore:`.
- **One PR per slice/change**, kept small and reviewable.
- Every control maps to a specific entry in `THREAT_MODEL.md` — reference it in the PR/commit when adding one.
- No real secrets, credentials, or employer-specific patterns in this repo — it's public.

## Commands

```
pip install -r requirements.txt          # install deps (run inside a venv)
uvicorn gateway.main:app --reload        # run the gateway locally
pytest                                   # run the test suite
python scripts/generate_client_key.py X  # register client X, print its API key once
python scripts/verify_audit_log.py       # check the audit log's hash chain is intact
```

`gateway/clients.json` (the local client registry) and `logs/audit.log` are both git-ignored — generated locally, never committed. Tests never touch either: `tests/conftest.py`'s `audit_log_path` fixture is `autouse=True` and redirects logging to a tmp file for every test. Same pattern for rate limiting: `reset_rate_limiter_state` is also `autouse=True`, and a `fake_clock` fixture lets time-based tests (refill, budget window reset) advance time deterministically instead of sleeping.

Rate limits are in-memory per-process (`gateway/rate_limiter.py`) — default 5 requests/client before throttling kicks in. Expect `429`s from manual testing if you script more than a handful of quick requests against one client.

A local-only demo UI (`gateway/static/index.html`, mounted at `/` in `gateway/main.py`) is served automatically by `uvicorn gateway.main:app` — plain HTML/CSS/JS, no build step, no framework. It's a thin client against `/v1/chat`; don't add backend behavior that only exists for the UI's sake.

## Docs map

- `README.md` — scope, priorities, build order, per-slice design decisions
- `THREAT_MODEL.md` — assets, actors, attack paths, trust boundaries, open design decisions
