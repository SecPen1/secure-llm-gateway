# Secure LLM Gateway

A reference implementation of a security-focused gateway sitting in front of an LLM API (Claude), built as a portfolio project demonstrating applied security architecture — not just working code, but the design decisions and trade-offs behind it.

**Status:** early planning stage — no application code yet. See the docs below for the design work done so far.

## Why this exists

This project is a hands-on demonstration of security architecture thinking applied to a real, if small, system: an LLM gateway that mediates access between client applications and an upstream LLM API. It's built slice-by-slice, with each control mapped back to a specific entry in the threat model and documented as it lands.

## Docs

- [PROJECT_HANDOFF.md](PROJECT_HANDOFF.md) — project scope, working style, and build order
- [THREAT_MODEL.md](THREAT_MODEL.md) — assets, actors, STRIDE-based attack paths, and trust boundaries

## Build order (v1)

1. Input validation & sanitization
2. Auth layer (per-client, scoped)
3. Prompt injection defenses
4. Output filtering
5. Audit logging
6. Rate limiting / cost controls

Each slice gets a working control, a README section explaining the design decision behind it, and a test or demo showing it functioning.

## Built with Claude Code

This repo is built in collaboration with [Claude Code](https://claude.com/claude-code) — Claude does the implementation work, under human direction and review, for every design decision, control, and trade-off documented here. See [CLAUDE.md](CLAUDE.md) for the working conventions used.

## License

[MIT](LICENSE)
