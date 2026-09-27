# CLAUDE.md

Reference doc for Claude Code sessions working in this repo. Keep this file short — put rationale and narrative in `PROJECT_HANDOFF.md` / `THREAT_MODEL.md`, not here.

## What this is

Secure LLM Gateway — a portfolio project (see [PROJECT_HANDOFF.md](PROJECT_HANDOFF.md) for full scope). Public repo; audience includes hiring managers, so code and docs both need to read cleanly.

## Status

Python 3.12 + FastAPI. Slices 1–5 done (input validation, auth layer, prompt injection defenses, output filtering, audit logging) — see `gateway/`. Next up: slice 6 (rate limiting / cost controls).

The LLM call itself is currently a deterministic stub (`gateway/llm_client.py`, `StubLLMClient`) — no real upstream API integration exists yet. Check `README.md` Slice 4 before assuming otherwise.

## Working conventions

- **Slice-by-slice**: build one control end-to-end (see Build Order in `PROJECT_HANDOFF.md`) before starting the next. Don't build ahead of v1 scope.
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

`gateway/clients.json` (the local client registry) and `logs/audit.log` are both git-ignored — generated locally, never committed. Tests never touch either: `tests/conftest.py`'s `audit_log_path` fixture is `autouse=True` and redirects logging to a tmp file for every test.

## Docs map

- `PROJECT_HANDOFF.md` — scope, priorities, build order, definition of done
- `THREAT_MODEL.md` — assets, actors, attack paths, trust boundaries, open design decisions
