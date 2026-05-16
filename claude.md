# AI Sales Outreach Automation — Project Context

> Claude Code reads this on every session. Keep it tight; deep details live in `/docs`.

## Multi-agent workflow
This project is built using both **Claude Code** and **OpenAI Codex**.
Before any work, read [`AGENTS.md`](AGENTS.md) (routing rules) and [`HANDOFF.md`](HANDOFF.md) (recent session log).
Announce your routing decision before touching code.
Update `HANDOFF.md` at the end of every session — template is at the top of that file.

## What This Is
A full-stack, AI-powered B2B sales outreach platform. It ingests leads from CSV/Sheets,
researches each company via LangGraph agents, generates hyper-personalized emails,
sends them through Gmail, tracks replies, schedules follow-ups, and syncs the CRM.

The product value is **personalization quality** — not "AI agents". Optimize for relevance.

## Architecture (high level)
```
Next.js (UI)  →  FastAPI (API)  →  LangGraph (reasoning)  →  n8n (automation)  →  External APIs
                       │                                                          (Gmail, HubSpot,
                       ▼                                                           Slack, Sheets)
              PostgreSQL + Qdrant + Redis
```
Detailed diagrams: [docs/00-ARCHITECTURE.md](docs/00-ARCHITECTURE.md)

**Mental model:** n8n is the *pipeline*, LangGraph is the *brain*. Never put reasoning in n8n.

## Tech Stack
- **Frontend:** Next.js 14 (App Router), TypeScript, Tailwind, shadcn/ui, TanStack Query
- **Backend:** FastAPI, Python 3.11, SQLAlchemy 2.0 (async), Alembic, Pydantic v2
- **Agents:** LangGraph, LangChain, OpenAI + Anthropic (Claude) APIs
- **Automation:** n8n (self-hosted via Docker)
- **Data:** PostgreSQL 15, Qdrant (vectors), Redis (rate limits + queues)
- **Deploy:** Docker Compose

## Directory Structure
```
/frontend       Next.js app                 → frontend/README.md
/backend        FastAPI app                 → backend/README.md
/agents         LangGraph agents (isolated) → agents/README.md
/n8n-workflows  Exported n8n JSON           → n8n-workflows/README.md
/infra          Docker Compose, nginx       → infra/README.md
/docs           Specs, diagrams, guides     → docs/README.md
```

## Documentation Index
| Doc | Purpose |
|-----|---------|
| [docs/00-ARCHITECTURE.md](docs/00-ARCHITECTURE.md) | System architecture & data flow |
| [docs/01-PHASES.md](docs/01-PHASES.md) | Phase-by-phase build plan (Phase 0 → 7) |
| [docs/02-DATABASE.md](docs/02-DATABASE.md) | Postgres schema + Qdrant collections |
| [docs/03-AGENTS.md](docs/03-AGENTS.md) | LangGraph agent specs (Research, Personalization, Compliance, Reply, Follow-up) |
| [docs/04-API.md](docs/04-API.md) | FastAPI route reference |
| [docs/05-N8N-WORKFLOWS.md](docs/05-N8N-WORKFLOWS.md) | n8n workflow specs |
| [docs/06-FRONTEND.md](docs/06-FRONTEND.md) | Frontend pages, components, state model |
| [docs/07-DEPLOYMENT.md](docs/07-DEPLOYMENT.md) | Docker Compose, env vars, Makefile |
| [docs/CLAUDE-CODE-GUIDE.md](docs/CLAUDE-CODE-GUIDE.md) | How to prompt Claude Code on this repo |

## Coding Conventions
- **Python:** `async`/`await` everywhere, Pydantic v2 models, full type hints, no `print` (use `logging`).
- **Frontend:** functional components only — no class components.
- **API responses** always use the shape `{ "data": ..., "error": null, "meta": {...} }`.
- **Every new module needs a test file.** Run `pytest` / `npm test` before claiming done.
- **All IDs are UUIDs**, all timestamps UTC.
- **Migrations are immutable** once committed — never edit a generated Alembic file.
- **All AI calls go through `/agents`** — backend services must not call OpenAI/Anthropic directly.
- **No secrets in code** — read from env, see `.env.example`.

## Environment Variables
See `.env.example` for the full list. Required for any feature work:
`DATABASE_URL`, `QDRANT_URL`, `REDIS_URL`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
`GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `N8N_WEBHOOK_URL`, `TAVILY_API_KEY`, `FIRECRAWL_API_KEY`.

## Current Status
*Update this section at the end of every phase. Keep prior phases as one-line summaries.*

- **Phase 0** — Scaffold: ✅ complete
- **Phase 1** — Data Layer: ✅ complete
- **Phase 2** — FastAPI Backend: ✅ complete (incl. Gmail OAuth + GmailService)
- **Phase 3** — LangGraph Agents: ✅ complete (3A Research, 3B Personalization, 3C Reply Classifier, 3D Follow-up)
- **Phase 4** — n8n Workflows: ⬜ not started
- **Phase 5** — Frontend: ⬜ not started
- **Phase 6** — Integration Tests: ⬜ not started 
- **Phase 7** — Docker & Deployment: ⬜ not started

## Working Agreements (read every session)
1. **One phase per session.** Do not mix Phase N work into a Phase N+1 session.
2. **End every task with a verification command.** "Run X, confirm output Y."
3. **Reference exact file paths and line numbers** when editing — never "fix the gmail service".
4. **Update the Current Status block** before finishing a phase.
5. **Track surprises in `scratchpad.md`** at the repo root (decisions, package choices, gotchas).

## Do NOT
- Do **not** install new packages without recording them in `requirements.txt` / `package.json`.
- Do **not** modify Alembic migration files once they are generated.
- Do **not** bypass the agent interface layer — all LLM calls flow through `/agents`.
- Do **not** put business logic into n8n — n8n only orchestrates HTTP + Gmail nodes.
- Do **not** hardcode secrets, OAuth tokens, or DB URLs anywhere.
- Do **not** use class components in the frontend.
- Do **not** add Redux/Zustand — React Query is the only data layer.
- Do **not** call `console.log` in committed code (frontend) or `print` in Python.
- Do **not** mock the database in integration tests — use a real Postgres test container.
- Do **not** over-engineer: prefer 3 similar lines over a premature abstraction.
