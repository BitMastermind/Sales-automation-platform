# AGENTS.md — Dual-Agent Routing Rules

This project is built using **Claude Code** and **OpenAI Codex** together. Both agents read this file at the start of every session.

**Companion file:** [`HANDOFF.md`](HANDOFF.md) — rolling log of the last 3 sessions. Read it after this file.

**Spec:** [`docs/superpowers/specs/2026-05-16-dual-agent-workflow-design.md`](docs/superpowers/specs/2026-05-16-dual-agent-workflow-design.md)

---

## Session start — every session, both agents

1. Read this file (`AGENTS.md`) and `HANDOFF.md`.
2. Announce a routing decision in chat, in one of two forms:
   - "Routing: task class = X → I am the correct agent, proceeding." OR
   - "Routing: task class = Y → switch to {other agent}. Stopping."
3. If Claude Code: also announce the current Claude 5h-window state from the most recent `HANDOFF.md` entry, plus the chosen model.

If the most recent `HANDOFF.md` entry is missing or stale (>24h), say so before proceeding.

---

## Routing rules — task-type first, usage as fallback

### Table A — Which agent

| Task class | Default agent | Why |
|---|---|---|
| Multi-file refactor / repo-wide rename | **Codex** | Heavy context, 1 message |
| Repo-wide review, audit, security sweep | **Codex** | Index whole codebase = 1 message |
| Generating tests across many files | **Codex** | Token-heavy in CC |
| Docs / README updates spanning many files | **Codex** | Same |
| Single-file feature work (e.g. Phase 3B agent) | **Claude Code** | Tight context, deep reasoning |
| Targeted bugfix in 1–2 files | **Claude Code** | Precision over breadth |
| Plan-mode architecture work, spec writing | **Claude Code** | Plan mode is cheap |
| Unit-test authoring for one module | **Claude Code (Haiku)** | Cheap, fast |
| Quick "what does this do" Q&A | **Claude Code** | Codex burns a message |

### Override rule (usage fallback)

If Claude Code has crossed ~80% of its current 5h rolling window (per the last `HANDOFF.md` entry), push **everything** to Codex until the window rolls over — including tasks normally routed to CC.

### Table B — Claude Code model selection

| Task | Model | Command |
|---|---|---|
| Hard architectural reasoning, ambiguous bugs | Opus 4.7 | `/model opus` |
| Default feature building | Sonnet 4.6 | `/model sonnet` |
| Unit tests, formatting, mechanical edits | Haiku 4.5 | `/model haiku` |

---

## Operational rules

- Run `/clear` every ~12 messages, or at the completion of any mini-feature.
- Use plan mode before any non-trivial implementation.
- Disable unused MCP servers — every connected server injects its tool schema into every prompt.
- Never call OpenAI / Anthropic directly from backend code — all LLM calls go through `/agents` (existing project rule).
- One phase per session (existing project rule).

---

## Session end — every session, both agents

1. Append a new entry to `HANDOFF.md` using the template at the top of that file.
2. If `HANDOFF.md` now has more than 3 entries, delete the oldest entry.
3. Commit the `HANDOFF.md` change with message: `chore: handoff log <YYYY-MM-DD> <agent>`.
