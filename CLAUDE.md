# CLAUDE.md

Reference doc for Claude Code sessions working in this repo. Keep this file short — put rationale and narrative in `PROJECT_HANDOFF.md` / `THREAT_MODEL.md`, not here.

## What this is

Secure LLM Gateway — a portfolio project (see [PROJECT_HANDOFF.md](PROJECT_HANDOFF.md) for full scope). Public repo; audience includes hiring managers, so code and docs both need to read cleanly.

## Status

Planning stage. No application code yet. Tech stack (Python/FastAPI vs Node/Express) not yet chosen — check `PROJECT_HANDOFF.md` before assuming one.

## Working conventions

- **Slice-by-slice**: build one control end-to-end (see Build Order in `PROJECT_HANDOFF.md`) before starting the next. Don't build ahead of v1 scope.
- **Conventional commits**: `feat:`, `fix:`, `docs:`, `chore:`.
- **One PR per slice/change**, kept small and reviewable.
- Every control maps to a specific entry in `THREAT_MODEL.md` — reference it in the PR/commit when adding one.
- No real secrets, credentials, or employer-specific patterns in this repo — it's public.

## Commands

None yet — this section gets filled in once a stack is chosen and a build system exists (test/lint/run commands go here).

## Docs map

- `PROJECT_HANDOFF.md` — scope, priorities, build order, definition of done
- `THREAT_MODEL.md` — assets, actors, attack paths, trust boundaries, open design decisions
