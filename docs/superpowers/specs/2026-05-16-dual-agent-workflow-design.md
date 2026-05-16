# Dual-Agent Workflow: Claude Code + OpenAI Codex

**Status:** Approved design — 2026-05-16
**Goal:** Maximize coding-agent uptime across the 2-month build window by routing tasks to the agent whose pricing model fits the work, with a shared handoff log so neither tool re-derives context.

## Why

- **Claude Code** charges by token volume. It burns out fast on context-heavy work (repo-wide reviews, multi-file refactors) but is cheap and deep for precision tasks.
- **OpenAI Codex** charges by message count. It is unaffected by repo size per prompt but exhausts fast under chatty micro-task patterns.

Optimal strategy: split by **context size**, not by preference. Heavy context → Codex (1 message). Tight context, deep reasoning → Claude Code.

Shared state lives in two files so neither tool re-derives where the other left off, which is the single biggest source of wasted tokens/messages.

## File layout

| File | Path | Purpose | Edit frequency | Size budget |
|---|---|---|---|---|
| `AGENTS.md` | repo root | Durable routing rules, model selection, operational rules, workflow loop | rarely | < 150 lines |
| `HANDOFF.md` | repo root | Rolling session log, hard-capped to last 3 entries | every session end | ~60 lines |
| `claude.md` | repo root (existing) | Add a pointer instructing Claude Code to read `AGENTS.md` and `HANDOFF.md` on session start | one-time edit | unchanged otherwise |

**Why two files:** `AGENTS.md` stays stable (good for prompt cache). `HANDOFF.md` churns and can be pruned without touching the rulebook. Codex reads `AGENTS.md` by convention with zero configuration.

## Routing rules (canonical, lives in `AGENTS.md`)

### Table A — Agent routing (task-type first)

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

If Claude Code has crossed ~80% of its current 5h rolling window, push everything to Codex until the window rolls over — including tasks normally routed to CC. The current window state is tracked in the latest `HANDOFF.md` entry.

### Table B — Claude Code model selection

| Task | Model | Command |
|---|---|---|
| Hard architectural reasoning, ambiguous bugs | Opus 4.7 | `/model opus` |
| Default feature building | Sonnet 4.6 | `/model sonnet` |
| Unit tests, formatting, mechanical edits | Haiku 4.5 | `/model haiku` |

### Operational rules (also in `AGENTS.md`)

- Run `/clear` every ~12 messages or at the completion of any mini-feature.
- Use plan mode before any non-trivial implementation.
- Disable unused MCP servers — every connected server injects its tool schema into every prompt.
- Never call OpenAI / Anthropic directly from backend code — all LLM calls go through `/agents` (existing project rule).
- One phase per session (existing project rule).

## Workflow loop

### Session start (either agent)

1. Read `AGENTS.md` (rules) and `HANDOFF.md` (last 3 entries).
2. Announce a routing decision in chat:
   - "Routing: task class = X → I am the correct agent, proceeding." OR
   - "Routing: task class = Y → switch to {other agent}. Stopping."
3. If Claude Code: announce the current 5h-window state from `HANDOFF.md` and the chosen model.

### Session end (either agent)

1. Append a new entry to `HANDOFF.md` (template below).
2. If `HANDOFF.md` now has more than 3 entries, delete the oldest.
3. Commit the `HANDOFF.md` change.

### `HANDOFF.md` entry template

```markdown
## 2026-05-16T14:30Z — Claude Code (Sonnet)
**Phase:** 3B Personalization Agent
**Did:** Implemented agents/personalization_agent.py + 6 unit tests passing.
**Next:** Wire backend route POST /api/personalization/draft; smoke test with real API.
**Claude window:** ~40% used, resets ~19:00Z.
**Handoff to:** Claude Code (continue) — single-file, precision work.
**Gotchas:** Pydantic v2 field_validator quirk on optional list — see line 84.
```

## Pointer to add to `claude.md`

Add near the top of `claude.md` (or `CLAUDE.md`):

```markdown
## Multi-agent workflow
This project is built using both Claude Code and OpenAI Codex.
Before any work, read `AGENTS.md` (routing rules) and `HANDOFF.md` (recent session log).
Announce your routing decision before touching code.
Update `HANDOFF.md` at the end of every session (template inside).
```

## Out of scope

- No SessionStart or Stop hooks. Pure discipline only.
- No automation script to prune `HANDOFF.md`. Agents prune manually as part of the end-of-session step.
- No tracking of Codex message budget in `HANDOFF.md` (Codex usage is opaque to Claude Code; user tracks it themselves).
- No per-phase log files. The single `HANDOFF.md` covers all phases.

## Success criteria

1. Starting a new Claude Code or Codex session requires zero re-explanation of what the previous session did — `HANDOFF.md` carries it.
2. The routing matrix in `AGENTS.md` answers "which agent for this task" without ambiguity for every task class encountered so far.
3. Across one full Phase 3 sub-phase (e.g. 3B), at least one agent switch happens cleanly based on the matrix, and the user does not retype context for the receiving agent.
4. Neither agent hits its hard limit before the corresponding phase is complete.

## Open risks

- **Discipline drift:** without hooks, agents may skip the end-of-session log when interrupted. Mitigation: the routing-decision announcement at session start makes the absence of a recent log immediately visible.
- **Codex conventions may change:** `AGENTS.md` is the current Codex convention — if it changes, this design needs a re-point.
- **Codex setup status:** this spec assumes Codex CLI / workspace is already configured for the user. If it is not, that is a prerequisite, not part of this design.
