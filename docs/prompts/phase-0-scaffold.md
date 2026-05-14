# Phase 0 — Project Scaffold

> **One session. No business logic. Only structure.**

---

## Session Setup

| | |
|---|---|
| **Model** | `claude-sonnet-4-6` |
| **Skills** | Invoke `writing-plans` before starting |
| **Estimated time** | 30–60 min |

### How to start this session
Open Claude Code in the repo root and type:
```
/skill writing-plans
```
Then paste the Phase 0 prompt below.

---

## Prompt

```
Read CLAUDE.md before starting.

## Context
This is Phase 0 of an AI Sales Outreach Automation platform. The goal is a clean project scaffold — no business logic, just structure that every later phase builds on.

Stack:
- Frontend: Next.js 14, TypeScript, Tailwind, shadcn/ui (App Router, src/ dir)
- Backend: FastAPI, Python 3.11, pyproject.toml (NOT requirements.txt), async SQLAlchemy 2.0, Alembic, Pydantic v2
- Agents: /agents directory, isolated from backend
- Infra: Docker Compose with postgres:15, qdrant/qdrant:latest, redis:7-alpine, n8nio/n8n:latest
- Make: root Makefile with shortcuts

## Tasks (execute in order)

### Task 1 — Next.js frontend
Run: npx create-next-app@latest frontend --typescript --tailwind --app --src-dir --no-eslint
Then install shadcn/ui: npx shadcn@latest init (choose Default style, slate base color, yes CSS variables)
Add: npm install @tanstack/react-query recharts react-dropzone
Create /frontend/src/app/layout.tsx with a basic sidebar shell (just divs, no logic yet).

### Task 2 — FastAPI backend
Create /backend/ with this exact structure:
  /backend
  ├── api/
  │   ├── __init__.py
  │   ├── campaigns.py      (empty router stub)
  │   ├── leads.py          (empty router stub)
  │   ├── emails.py         (empty router stub)
  │   ├── webhooks.py       (empty router stub)
  │   └── auth.py           (empty router stub)
  ├── core/
  │   ├── __init__.py
  │   ├── config.py         (Pydantic Settings reading from env)
  │   ├── database.py       (async SQLAlchemy engine + session factory)
  │   └── logging.py        (structured logging setup)
  ├── models/
  │   └── __init__.py
  ├── services/
  │   └── __init__.py
  ├── agents_interface/
  │   └── __init__.py       (stub: comment explaining this is the ONLY way backend calls agents)
  ├── tests/
  │   ├── __init__.py
  │   └── conftest.py       (pytest-asyncio setup, async DB session fixture)
  ├── main.py               (FastAPI app, CORS middleware, router includes, /health endpoint)
  ├── pyproject.toml        (with all deps listed below)
  └── alembic.ini

pyproject.toml must include these dependencies (do NOT add extras not on this list):
  fastapi>=0.115, uvicorn[standard], sqlalchemy>=2.0, alembic, asyncpg,
  pydantic>=2.0, pydantic-settings, httpx, qdrant-client, redis[asyncio],
  google-auth, google-auth-oauthlib, google-api-python-client,
  python-multipart, cryptography, pytest, pytest-asyncio, respx, factory-boy

### Task 3 — Agents directory
Create /agents/ with:
  /agents
  ├── __init__.py
  ├── research_agent.py     (stub with function signature only)
  ├── personalization_agent.py  (stub)
  ├── reply_classifier.py   (stub)
  ├── followup_agent.py     (stub)
  └── prompts/
      └── __init__.py

Each stub should define the entry-point function signature with correct type hints and a NotImplementedError body.

### Task 4 — .env.example
Create at the repo root:
  DATABASE_URL=postgresql+asyncpg://sales:sales@postgres:5432/sales
  QDRANT_URL=http://qdrant:6333
  REDIS_URL=redis://redis:6379/0
  OPENAI_API_KEY=
  ANTHROPIC_API_KEY=
  TAVILY_API_KEY=
  FIRECRAWL_API_KEY=
  GMAIL_CLIENT_ID=
  GMAIL_CLIENT_SECRET=
  N8N_WEBHOOK_URL=http://n8n:5678/webhook
  INTERNAL_API_TOKEN=change-me-at-least-32-chars-random
  NEXT_PUBLIC_API_BASE=http://localhost:8000

### Task 5 — Docker Compose
Create /infra/docker-compose.yml:
  Services: postgres, qdrant, redis, n8n, backend, frontend
  - All have healthchecks
  - All share network "saleshq"
  - backend depends_on: postgres, qdrant, redis (condition: service_healthy)
  - Volumes: pgdata, qdrantdata, redisdata, n8ndata
  - backend and frontend mount source dirs for hot reload in dev

### Task 6 — Makefile at repo root
Commands:
  make dev      → docker compose -f infra/docker-compose.yml up --build
  make migrate  → docker compose exec backend alembic upgrade head
  make test     → docker compose exec backend pytest -v
  make lint     → ruff check + mypy (backend), eslint (frontend)
  make seed     → docker compose exec backend python scripts/seed.py

### Task 7 — Alembic init
Run: cd backend && alembic init alembic
Edit alembic/env.py to use the async SQLAlchemy engine from core/database.py.
Set sqlalchemy.url in alembic.ini to read from env variable DATABASE_URL.

### Task 8 — scratchpad.md
Create scratchpad.md at the repo root with this exact header:
  # Project Scratchpad
  ## Phase 0 — Scaffold (date: today)
  - [Add your notes here as you work]

## Constraints
- Do NOT implement any route logic, models, or agent logic.
- Do NOT use requirements.txt — use pyproject.toml only.
- Do NOT add packages beyond the list in Task 2.
- Do NOT touch the frontend beyond the shadcn/ui init and the layout shell.
- Do NOT create a database migration yet — that is Phase 1.

## Verify
Run: docker compose -f infra/docker-compose.yml config
Expected: Parses cleanly, no YAML errors, all services listed.

Then run: cd backend && python -c "from main import app; print('OK')"
Expected: "OK" (no import errors)

Then run: cd frontend && npx tsc --noEmit
Expected: Zero type errors.

When all three pass, update CLAUDE.md Current Status: Phase 0 → ✅ complete.
```

---

## After This Session
1. Run all three verify commands above.
2. Append to `scratchpad.md`: any packages you couldn't find, any directory decisions that differed from the plan.
3. Update CLAUDE.md: `Phase 0 — ✅ complete`.
4. Commit.
