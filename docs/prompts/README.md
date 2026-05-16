# /docs/prompts — Session Prompts (Claude Code + Codex)

One file per domain area. Each file contains all phases for that domain with:
- **Agent** — Claude Code or Codex (see routing rules in [AGENTS.md](../../AGENTS.md))
- **Model** — which Claude model to use (Claude Code sessions only)
- **Skills** — which superpowers skill to invoke first (Claude Code sessions only)
- **Prompt** — the exact text to paste into either agent
- **Verify** — the command(s) to run to confirm the work is done

## Files

| File | Phases | Domain |
|------|--------|--------|
| [phase-0-scaffold.md](phase-0-scaffold.md) | 0 | Project scaffold, Docker skeleton, Makefile |
| [phase-1-2-backend.md](phase-1-2-backend.md) | 1A, 1B, 2A, 2B | Data layer (Postgres + Qdrant) + FastAPI routes + Gmail OAuth |
| [phase-3-agents.md](phase-3-agents.md) | 3A, 3B, 3C, 3D | LangGraph agents (Research, Personalization, Classifier, Follow-up) |
| [phase-4-automation.md](phase-4-automation.md) | 4 | n8n workflow JSON + credential setup |
| [phase-5-frontend.md](phase-5-frontend.md) | 5A, 5B | Next.js dashboard + campaign creation flow |
| [phase-6-7-testing-deploy.md](phase-6-7-testing-deploy.md) | 6, 7 | Integration tests + Docker Compose production setup |

## Quick Reference — Agent + Model + Skills Per Phase

| Phase | Sub | Status | Agent | Model | Skills (CC only) |
|-------|-----|--------|-------|-------|-----------------|
| 0 | Scaffold | ✅ done | Codex | n/a | — |
| 1A | Postgres schema | ✅ done | Claude Code | `claude-sonnet-4-6` | `test-driven-development` |
| 1B | Qdrant | ✅ done | Claude Code | `claude-sonnet-4-6` | `test-driven-development` |
| 2A | FastAPI routes | ✅ done | Claude Code | `claude-sonnet-4-6` | `test-driven-development` |
| 2B | Gmail OAuth | ✅ done | Claude Code | `claude-sonnet-4-6` | `test-driven-development` |
| 3A | Research agent | ✅ done | Claude Code | `claude-opus-4-7` | `brainstorming` → `test-driven-development` |
| 3B | Personalization agent | 🟡 next | **Claude Code** | `claude-opus-4-7` | `brainstorming` → `test-driven-development` |
| 3C | Reply classifier | ⬜ | **Claude Code** | `claude-sonnet-4-6` | `test-driven-development` |
| 3D | Follow-up agent | ⬜ | **Claude Code** | `claude-opus-4-7` | `brainstorming` → `test-driven-development` |
| 4 | n8n workflows | ⬜ | **Codex** | n/a | — |
| 5A Pass 1 | Dashboard — design first page | ⬜ | **Claude Code** | `claude-opus-4-7` | `frontend-design` |
| 5A Pass 2 | Dashboard — remaining pages | ⬜ | **Codex** | n/a | — |
| 5B | Campaign creation | ⬜ | **Claude Code** | `claude-opus-4-7` | `brainstorming` → `frontend-design` |
| 6 | Integration tests | ⬜ | **Codex** | n/a | — |
| 7 | Docker + deploy | ⬜ | **Codex** | n/a | — |

## How to Use

### Claude Code sessions
1. Open Claude Code in the repo root (`/Users/ashitverma/Sales Automation`).
2. Switch model: `/model <name>` (see table above).
3. Invoke the skill: `/skill <name>` and follow its instructions.
4. Paste the **Prompt** block from the relevant phase file.
5. Run the **Verify** command. Do not move on until it passes.
6. Append a session entry to `HANDOFF.md`, then commit.

### Codex sessions
1. Open a Codex session pointed at the repo root. Codex auto-reads `AGENTS.md`.
2. Confirm routing: Codex should announce "Routing: task class = X → I am the correct agent."
3. Paste the **Prompt** block from the relevant phase file directly.
4. Run all **Verify** commands in the terminal yourself (Codex doesn't run `/skill` commands).
5. Append a session entry to `HANDOFF.md`, then commit.

## Rules
- **One sub-phase per session.** Don't blend 2A and 2B in the same conversation.
- **Always start by reading AGENTS.md + HANDOFF.md** before any code.
- **Claude Code: invoke skills before any code** — not after you've already started.
- **Verification is not optional** — if the verify command fails, the phase is not complete.
- **Always update HANDOFF.md at session end** — template is at the top of that file.
