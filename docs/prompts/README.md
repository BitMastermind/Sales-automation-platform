# /docs/prompts — Claude Code Session Prompts

One file per domain area. Each file contains all phases for that domain with:
- **Model** — which Claude model to use
- **Skills** — which superpowers skill to invoke first
- **Prompt** — the exact text to paste into Claude Code
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

## Quick Reference — Model + Skills Per Phase

| Phase | Sub | Model | Skills to invoke |
|-------|-----|-------|-----------------|
| 0 | Scaffold | `claude-sonnet-4-6` | `writing-plans` |
| 1A | Postgres schema | `claude-sonnet-4-6` | `test-driven-development` |
| 1B | Qdrant | `claude-sonnet-4-6` | `test-driven-development` |
| 2A | FastAPI routes | `claude-sonnet-4-6` | `test-driven-development` |
| 2B | Gmail OAuth | `claude-sonnet-4-6` | `test-driven-development` |
| 3A | Research agent | `claude-opus-4-7` | `brainstorming` → `test-driven-development` |
| 3B | Personalization agent | `claude-opus-4-7` | `brainstorming` → `test-driven-development` |
| 3C | Reply classifier | `claude-opus-4-7` | `test-driven-development` |
| 3D | Follow-up agent | `claude-opus-4-7` | `brainstorming` → `test-driven-development` |
| 4 | n8n workflows | `claude-sonnet-4-6` | none |
| 5A | Dashboard + pages | `claude-opus-4-7` | `frontend-design` |
| 5B | Campaign creation | `claude-opus-4-7` | `brainstorming` → `frontend-design` |
| 6 | Integration tests | `claude-sonnet-4-6` | `verification-before-completion` |
| 7 | Docker + deploy | `claude-sonnet-4-6` | `verification-before-completion` |

## How to Use

1. Open Claude Code in the repo root (`/Users/ashitverma/Sales Automation`).
2. Check the model: type `/model` and switch if needed (see table above).
3. Invoke the skill listed: type `/skill <name>` and follow its instructions.
4. Paste the **Prompt** block from the relevant file.
5. At the end, run the **Verify** command. Do not move to the next phase until it passes.
6. Update `CLAUDE.md` Current Status and commit.

## Rules
- **One sub-phase per session.** Don't blend 2A and 2B in the same conversation.
- **Always start by reading CLAUDE.md** — the prompt text begins with "Read CLAUDE.md".
- **Invoke skills before any code** — not after you've already started.
- **Verification is not optional** — if the verify command fails, the phase is not complete.
