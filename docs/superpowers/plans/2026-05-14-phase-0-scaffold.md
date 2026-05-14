# Phase 0 — Project Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the full project scaffold — directory structure, tooling, env config, and Docker skeleton — with zero business logic.

**Architecture:** Three isolated code planes: Next.js frontend, FastAPI backend, and LangGraph agents. They share a Docker Compose network but never import from each other at the module level. The only bridge allowed is `backend/agents_interface/`. All directories (`backend/`, `frontend/`, `agents/`, `infra/`) already exist with only `README.md` files inside.

**Tech Stack:** Next.js 14 (App Router, TypeScript, Tailwind, shadcn/ui), FastAPI + Python 3.11 (pyproject.toml, async SQLAlchemy 2.0, Alembic, Pydantic v2), agent stubs in `/agents`, Docker Compose with postgres:15, qdrant, redis:7-alpine, n8nio/n8n.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/pyproject.toml` | Create | All Python deps, pytest config |
| `backend/main.py` | Create | FastAPI app, CORS, router mounts, /health |
| `backend/core/config.py` | Create | Pydantic Settings from env |
| `backend/core/database.py` | Create | Async SQLAlchemy engine + session factory |
| `backend/core/logging.py` | Create | Structured JSON logging setup |
| `backend/api/{campaigns,leads,emails,webhooks,auth}.py` | Create | Empty APIRouter stubs |
| `backend/agents_interface/__init__.py` | Create | Boundary comment stub |
| `backend/tests/conftest.py` | Create | pytest-asyncio setup |
| `backend/tests/test_health.py` | Create | Smoke test for /health |
| `backend/Dockerfile` | Create | Multi-stage dev build |
| `backend/alembic/env.py` | Create (via alembic init + edit) | Async Alembic migrations driver |
| `agents/research_agent.py` | Create | Entry-point stub |
| `agents/personalization_agent.py` | Create | Entry-point stub |
| `agents/reply_classifier.py` | Create | Entry-point stub |
| `agents/followup_agent.py` | Create | Entry-point stub |
| `.env.example` | Create | All required env keys |
| `infra/docker-compose.yml` | Create | All 6 services with healthchecks |
| `frontend/Dockerfile` | Create | Dev Node image |
| `frontend/src/app/layout.tsx` | Modify (after create-next-app) | Sidebar shell |
| `Makefile` | Create | dev/migrate/test/lint/seed |
| `scratchpad.md` | Create | Phase notes |

---

## Task 1: FastAPI backend — pyproject.toml + core files

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/main.py`
- Create: `backend/core/__init__.py`
- Create: `backend/core/config.py`
- Create: `backend/core/database.py`
- Create: `backend/core/logging.py`
- Create: `backend/models/__init__.py`
- Create: `backend/services/__init__.py`
- Test: `backend/tests/test_health.py`

- [ ] **Step 1: Write the failing health test first**

Create `backend/tests/__init__.py` (empty) and `backend/tests/test_health.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_health_returns_ok():
    # Import here so the test fails loudly if main.py is missing
    from main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["status"] == "ok"
    assert body["error"] is None
```

- [ ] **Step 2: Verify the test fails (main.py missing)**

Run from `backend/`:
```bash
cd /path/to/repo/backend
python -m pytest tests/test_health.py -v
```
Expected: `ModuleNotFoundError: No module named 'main'`  — confirms test is wired correctly.

- [ ] **Step 3: Create `backend/pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "sales-automation-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]",
    "sqlalchemy>=2.0",
    "alembic",
    "asyncpg",
    "pydantic>=2.0",
    "pydantic-settings",
    "httpx",
    "qdrant-client",
    "redis[asyncio]",
    "google-auth",
    "google-auth-oauthlib",
    "google-api-python-client",
    "python-multipart",
    "cryptography",
    "pytest",
    "pytest-asyncio",
    "respx",
    "factory-boy",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
target-version = "py311"
```

- [ ] **Step 4: Create `backend/core/__init__.py`** (empty file)

- [ ] **Step 5: Create `backend/core/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://sales:sales@localhost:5432/sales"
    qdrant_url: str = "http://localhost:6333"
    redis_url: str = "redis://localhost:6379/0"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    tavily_api_key: str = ""
    firecrawl_api_key: str = ""
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    n8n_webhook_url: str = "http://localhost:5678/webhook"
    internal_api_token: str = "change-me-at-least-32-chars-random"
    next_public_api_base: str = "http://localhost:8000"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
```

- [ ] **Step 6: Create `backend/core/database.py`**

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from core.config import settings

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 7: Create `backend/core/logging.py`**

```python
import logging
import sys


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "msg": "%(message)s"}',
        stream=sys.stdout,
    )
```

- [ ] **Step 8: Create `backend/models/__init__.py`** (empty)

- [ ] **Step 9: Create `backend/services/__init__.py`** (empty)

- [ ] **Step 10: Create `backend/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.logging import setup_logging

setup_logging()

app = FastAPI(title="Sales Automation API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"data": {"status": "ok"}, "error": None, "meta": {}}
```

Note: Router includes are added in Task 2 after the router files exist.

- [ ] **Step 11: Install dependencies and run the test**

```bash
cd backend
pip install -e ".[dev]" 2>/dev/null || pip install -e .
python -m pytest tests/test_health.py -v
```
Expected:
```
tests/test_health.py::test_health_returns_ok PASSED
1 passed in ...s
```

- [ ] **Step 12: Verify clean import**

```bash
cd backend
python -c "from main import app; print('OK')"
```
Expected: `OK`

- [ ] **Step 13: Commit**

```bash
git add backend/pyproject.toml backend/main.py backend/core/ backend/models/__init__.py backend/services/__init__.py backend/tests/
git commit -m "feat(scaffold): FastAPI core structure with /health endpoint"
```

---

## Task 2: FastAPI API router stubs

**Files:**
- Create: `backend/api/__init__.py`
- Create: `backend/api/campaigns.py`
- Create: `backend/api/leads.py`
- Create: `backend/api/emails.py`
- Create: `backend/api/webhooks.py`
- Create: `backend/api/auth.py`
- Modify: `backend/main.py` (add router includes)

- [ ] **Step 1: Create `backend/api/__init__.py`** (empty)

- [ ] **Step 2: Create `backend/api/campaigns.py`**

```python
from fastapi import APIRouter

router = APIRouter(prefix="/campaigns", tags=["campaigns"])
```

- [ ] **Step 3: Create `backend/api/leads.py`**

```python
from fastapi import APIRouter

router = APIRouter(prefix="/leads", tags=["leads"])
```

- [ ] **Step 4: Create `backend/api/emails.py`**

```python
from fastapi import APIRouter

router = APIRouter(prefix="/emails", tags=["emails"])
```

- [ ] **Step 5: Create `backend/api/webhooks.py`**

```python
from fastapi import APIRouter

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
```

- [ ] **Step 6: Create `backend/api/auth.py`**

```python
from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])
```

- [ ] **Step 7: Update `backend/main.py` to include routers**

Replace the existing `main.py` with:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.campaigns import router as campaigns_router
from api.leads import router as leads_router
from api.emails import router as emails_router
from api.webhooks import router as webhooks_router
from api.auth import router as auth_router
from core.logging import setup_logging

setup_logging()

app = FastAPI(title="Sales Automation API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(campaigns_router, prefix="/api")
app.include_router(leads_router, prefix="/api")
app.include_router(emails_router, prefix="/api")
app.include_router(webhooks_router, prefix="/api")
app.include_router(auth_router, prefix="/api")


@app.get("/health")
async def health() -> dict:
    return {"data": {"status": "ok"}, "error": None, "meta": {}}
```

- [ ] **Step 8: Re-run health test to confirm routers don't break it**

```bash
cd backend
python -m pytest tests/test_health.py -v
```
Expected: `PASSED`

- [ ] **Step 9: Commit**

```bash
git add backend/api/ backend/main.py
git commit -m "feat(scaffold): add empty API router stubs"
```

---

## Task 3: Agents interface + test conftest

**Files:**
- Create: `backend/agents_interface/__init__.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Create `backend/agents_interface/__init__.py`**

```python
# This package is the ONLY interface through which backend code may invoke agents.
# Backend services MUST NOT import from /agents directly.
# All LLM/agent calls must be routed through functions defined in this package.
# This enforces the plane separation described in docs/00-ARCHITECTURE.md.
```

- [ ] **Step 2: Create `backend/tests/conftest.py`**

```python
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DB_URL = "postgresql+asyncpg://sales:sales@localhost:5432/sales_test"


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine(TEST_DB_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()
```

Note: This fixture will fail until Phase 1 creates the schema and a real test DB is available. The conftest is scaffold-only here.

- [ ] **Step 3: Commit**

```bash
git add backend/agents_interface/ backend/tests/conftest.py
git commit -m "feat(scaffold): agents_interface boundary stub + test conftest"
```

---

## Task 4: Alembic initialization

**Files:**
- Creates (via command): `backend/alembic/` directory tree + `backend/alembic.ini`
- Modify: `backend/alembic/env.py`

- [ ] **Step 1: Run alembic init**

```bash
cd backend
alembic init alembic
```
Expected output: `Creating directory .../backend/alembic ... done` and several files created.

- [ ] **Step 2: Edit `backend/alembic.ini` — set sqlalchemy.url to a placeholder**

Find line:
```
sqlalchemy.url = driver://user:pass@localhost/dbname
```
Replace with:
```
sqlalchemy.url = postgresql+asyncpg://sales:sales@localhost:5432/sales
```
(env.py will override this from `DATABASE_URL` at runtime — the ini value is only used for `--url` overrides)

- [ ] **Step 3: Replace `backend/alembic/env.py` with async version**

```python
import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

config = context.config

# Override sqlalchemy.url from DATABASE_URL env var if present
if db_url := os.environ.get("DATABASE_URL"):
    config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# target_metadata will be populated in Phase 1 when models exist
# For Phase 0 we set it to None — autogenerate will produce an empty migration
try:
    from core.database import Base
    target_metadata = Base.metadata
except Exception:
    target_metadata = None  # noqa: F841


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 4: Verify alembic config is valid**

```bash
cd backend
python -c "from alembic.config import Config; c = Config('alembic.ini'); print('alembic OK')"
```
Expected: `alembic OK`

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/ backend/alembic.ini
git commit -m "feat(scaffold): initialize Alembic with async engine"
```

---

## Task 5: Agents directory stubs

**Files:**
- Create: `agents/__init__.py`
- Create: `agents/research_agent.py`
- Create: `agents/personalization_agent.py`
- Create: `agents/reply_classifier.py`
- Create: `agents/followup_agent.py`
- Create: `agents/prompts/__init__.py`

- [ ] **Step 1: Create `agents/__init__.py`** (empty)

- [ ] **Step 2: Create `agents/prompts/__init__.py`** (empty)

- [ ] **Step 3: Create `agents/research_agent.py`**

```python
from typing import Any


async def run_research_agent(lead: dict[str, Any]) -> dict[str, Any]:
    """Research a company and return structured research data.

    Args:
        lead: Dict with at minimum 'company_name' and 'website'.

    Returns:
        Structured research dict matching ResearchOutput schema (see docs/03-AGENTS.md).
    """
    raise NotImplementedError
```

- [ ] **Step 4: Create `agents/personalization_agent.py`**

```python
from typing import Any


async def run_personalization_agent(
    lead: dict[str, Any],
    research: dict[str, Any],
    campaign_context: dict[str, Any],
) -> dict[str, Any]:
    """Generate a personalized outreach email.

    Returns:
        Dict with keys: subject, opening_line, body, cta, full_email.
    """
    raise NotImplementedError
```

- [ ] **Step 5: Create `agents/reply_classifier.py`**

```python
from typing import Any


async def run_reply_classifier(
    reply_text: str,
    prior_email: str | None = None,
) -> dict[str, Any]:
    """Classify an inbound reply intent.

    Returns:
        Dict with keys: intent, confidence, suggested_next_action, key_phrases.
    """
    raise NotImplementedError
```

- [ ] **Step 6: Create `agents/followup_agent.py`**

```python
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


async def run_followup_agent(
    lead_id: str,
    db_session: AsyncSession,
) -> dict[str, Any]:
    """Generate a follow-up email or signal should_send=false.

    Returns:
        Dict with keys: should_send, subject, body, strategy.
    """
    raise NotImplementedError
```

- [ ] **Step 7: Verify stubs import cleanly**

```bash
cd /path/to/repo
python -c "
import asyncio, sys
sys.path.insert(0, 'agents')
from research_agent import run_research_agent
from personalization_agent import run_personalization_agent
from reply_classifier import run_reply_classifier
print('agents stubs OK')
"
```
Expected: `agents stubs OK`

- [ ] **Step 8: Commit**

```bash
git add agents/
git commit -m "feat(scaffold): agent stub entry points with typed signatures"
```

---

## Task 6: .env.example

**Files:**
- Create: `.env.example`

- [ ] **Step 1: Create `.env.example` at repo root**

```dotenv
# Postgres
DATABASE_URL=postgresql+asyncpg://sales:sales@postgres:5432/sales

# Qdrant
QDRANT_URL=http://qdrant:6333

# Redis
REDIS_URL=redis://redis:6379/0

# LLMs
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Research tooling
TAVILY_API_KEY=
FIRECRAWL_API_KEY=

# Gmail OAuth
GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=

# n8n
N8N_WEBHOOK_URL=http://n8n:5678/webhook
INTERNAL_API_TOKEN=change-me-at-least-32-chars-random

# Frontend
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

- [ ] **Step 2: Commit**

```bash
git add .env.example
git commit -m "feat(scaffold): .env.example with all required keys"
```

---

## Task 7: Docker Compose + Dockerfiles

**Files:**
- Create: `infra/docker-compose.yml`
- Create: `backend/Dockerfile`
- Create: `backend/.dockerignore`
- Create: `frontend/Dockerfile`
- Create: `frontend/.dockerignore`

- [ ] **Step 1: Create `backend/Dockerfile`**

```dockerfile
# --- builder ---
FROM python:3.11-slim AS builder
WORKDIR /build
COPY pyproject.toml .
RUN pip install --prefix=/install .

# --- runtime ---
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .
RUN useradd -m app && chown -R app:app /app
USER app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

- [ ] **Step 2: Create `backend/.dockerignore`**

```
__pycache__
*.pyc
.venv
.env
.env.*
!.env.example
alembic/versions/
*.egg-info
.mypy_cache
.ruff_cache
```

- [ ] **Step 3: Create `frontend/Dockerfile`** (dev image — Next.js production multi-stage is Phase 7)

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
CMD ["npm", "run", "dev"]
```

- [ ] **Step 4: Create `frontend/.dockerignore`**

```
node_modules
.next
.env
.env.*
!.env.example
```

- [ ] **Step 5: Create `infra/docker-compose.yml`**

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: sales
      POSTGRES_PASSWORD: sales
      POSTGRES_DB: sales
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - saleshq
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U sales"]
      interval: 10s
      timeout: 5s
      retries: 5

  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - qdrantdata:/qdrant/storage
    ports:
      - "6333:6333"
    networks:
      - saleshq
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:6333/healthz || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redisdata:/data
    ports:
      - "6379:6379"
    networks:
      - saleshq
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  n8n:
    image: n8nio/n8n:latest
    volumes:
      - n8ndata:/home/node/.n8n
    ports:
      - "5678:5678"
    environment:
      - N8N_HOST=n8n
      - N8N_PORT=5678
      - N8N_PROTOCOL=http
      - GENERIC_TIMEZONE=UTC
    networks:
      - saleshq
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:5678/healthz || exit 1"]
      interval: 15s
      timeout: 10s
      retries: 5

  backend:
    build:
      context: ../backend
      dockerfile: Dockerfile
    volumes:
      - ../backend:/app
    ports:
      - "8000:8000"
    env_file:
      - ../.env
    environment:
      DATABASE_URL: postgresql+asyncpg://sales:sales@postgres:5432/sales
      QDRANT_URL: http://qdrant:6333
      REDIS_URL: redis://redis:6379/0
    networks:
      - saleshq
    depends_on:
      postgres:
        condition: service_healthy
      qdrant:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:8000/health || exit 1"]
      interval: 15s
      timeout: 10s
      retries: 5

  frontend:
    build:
      context: ../frontend
      dockerfile: Dockerfile
    volumes:
      - ../frontend:/app
      - /app/node_modules
      - /app/.next
    ports:
      - "3000:3000"
    env_file:
      - ../.env
    networks:
      - saleshq
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:3000 || exit 1"]
      interval: 15s
      timeout: 10s
      retries: 5

networks:
  saleshq:
    driver: bridge

volumes:
  pgdata:
  qdrantdata:
  redisdata:
  n8ndata:
```

- [ ] **Step 6: Verify docker-compose config parses**

```bash
docker compose -f infra/docker-compose.yml config
```
Expected: Full YAML printed with no errors, all 6 services listed.

- [ ] **Step 7: Commit**

```bash
git add infra/docker-compose.yml backend/Dockerfile backend/.dockerignore frontend/Dockerfile frontend/.dockerignore
git commit -m "feat(scaffold): Docker Compose with 6 services and healthchecks"
```

---

## Task 8: Makefile

**Files:**
- Create: `Makefile`

- [ ] **Step 1: Create `Makefile` at repo root**

```makefile
.PHONY: dev migrate test lint seed

dev: ## Boot the full stack with logs
	docker compose -f infra/docker-compose.yml up --build

migrate: ## Run Alembic migrations inside backend container
	docker compose -f infra/docker-compose.yml exec backend alembic upgrade head

test: ## Run pytest inside backend container
	docker compose -f infra/docker-compose.yml exec backend pytest -v

lint: ## Ruff + mypy (backend), eslint (frontend)
	docker compose -f infra/docker-compose.yml exec backend ruff check .
	docker compose -f infra/docker-compose.yml exec backend mypy .
	docker compose -f infra/docker-compose.yml exec frontend npm run lint

seed: ## Create one demo campaign with 3 leads
	docker compose -f infra/docker-compose.yml exec backend python scripts/seed.py
```

- [ ] **Step 2: Verify Makefile syntax**

```bash
make --dry-run dev
```
Expected: Prints `docker compose -f infra/docker-compose.yml up --build` with no errors.

- [ ] **Step 3: Commit**

```bash
git add Makefile
git commit -m "feat(scaffold): Makefile with dev/migrate/test/lint/seed"
```

---

## Task 9: Next.js frontend bootstrap + layout shell

**Files:**
- Run: `npx create-next-app@latest` (overwrites `frontend/` except README.md)
- Modify: `frontend/src/app/layout.tsx`

- [ ] **Step 1: Move existing README to avoid conflict**

```bash
mv frontend/README.md frontend/README.original.md
```

- [ ] **Step 2: Bootstrap Next.js (answer all prompts with defaults except as shown)**

```bash
npx create-next-app@latest frontend --typescript --tailwind --app --src-dir --no-eslint --yes
```
Expected: `Success! Created frontend at .../frontend`

If `--yes` isn't honoured interactively, answer: TypeScript=Yes, Tailwind=Yes, App Router=Yes, src/ dir=Yes, import alias=No.

- [ ] **Step 3: Install shadcn/ui**

```bash
cd frontend
npx shadcn@latest init --defaults
```
If prompted: Style=Default, Base color=Slate, CSS variables=Yes.

- [ ] **Step 4: Install remaining frontend deps**

```bash
cd frontend
npm install @tanstack/react-query recharts react-dropzone
```
Expected: 3 packages added, no peer-dep errors.

- [ ] **Step 5: Replace `frontend/src/app/layout.tsx` with sidebar shell**

```tsx
import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import "./globals.css";

export const metadata: Metadata = {
  title: "SalesHQ",
  description: "AI-powered B2B sales outreach",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={GeistSans.className}>
        <div className="flex h-screen bg-background">
          <aside className="w-56 border-r flex flex-col p-4 shrink-0">
            <div className="font-semibold text-sm mb-6 px-2">SalesHQ</div>
            <nav className="flex flex-col gap-1 text-sm text-muted-foreground">
              {["Dashboard", "Campaigns", "Leads", "Templates", "Integrations", "Settings"].map(
                (item) => (
                  <div key={item} className="px-2 py-1.5 rounded hover:bg-muted cursor-pointer">
                    {item}
                  </div>
                )
              )}
            </nav>
          </aside>
          <div className="flex-1 flex flex-col overflow-hidden">
            <header className="border-b h-14 flex items-center px-6 text-sm font-medium shrink-0">
              SalesHQ Workspace
            </header>
            <main className="flex-1 overflow-auto p-6">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
```

Note: If `geist/font/sans` is not available, use `next/font/local` or fall back to `Inter` from `next/font/google`. Adjust the import to match whatever `create-next-app` generated.

- [ ] **Step 6: Verify TypeScript compiles**

```bash
cd frontend
npx tsc --noEmit
```
Expected: Zero errors, zero output.

- [ ] **Step 7: Commit**

```bash
git add frontend/
git commit -m "feat(scaffold): Next.js 14 bootstrap with shadcn/ui and sidebar shell"
```

---

## Task 10: scratchpad.md

**Files:**
- Create: `scratchpad.md`

- [ ] **Step 1: Create `scratchpad.md` at repo root**

```markdown
# Project Scratchpad

## Phase 0 — Scaffold (2026-05-14)

- [Add surprises, package gotchas, or directory decisions that differed from the plan here]
```

- [ ] **Step 2: Commit**

```bash
git add scratchpad.md
git commit -m "chore: add scratchpad for phase notes"
```

---

## Task 11: Final verification + CLAUDE.md update

- [ ] **Step 1: docker-compose config**

```bash
docker compose -f infra/docker-compose.yml config
```
Expected: Full YAML printed cleanly. All 6 services listed: postgres, qdrant, redis, n8n, backend, frontend.

- [ ] **Step 2: Backend import smoke test**

```bash
cd backend
python -c "from main import app; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Frontend TypeScript check**

```bash
cd frontend
npx tsc --noEmit
```
Expected: Zero type errors.

- [ ] **Step 4: Backend health test**

```bash
cd backend
python -m pytest tests/test_health.py -v
```
Expected: `1 passed`

- [ ] **Step 5: Update CLAUDE.md Current Status**

In [CLAUDE.md](../../CLAUDE.md), change:
```
- **Phase 0** — Scaffold: ⬜ not started
```
to:
```
- **Phase 0** — Scaffold: ✅ complete
```

- [ ] **Step 6: Final commit**

```bash
git add CLAUDE.md
git commit -m "chore: mark Phase 0 complete in CLAUDE.md"
```

---

## Self-Review Checklist

All 8 spec tasks covered:

| Spec Task | Plan Task |
|-----------|-----------|
| Next.js frontend + shadcn/ui + extra deps + layout.tsx | Task 9 |
| FastAPI backend structure + pyproject.toml | Tasks 1–3 |
| .env.example | Task 6 |
| Docker Compose skeleton with healthchecks | Task 7 |
| Makefile (dev/test/migrate/lint/seed) | Task 8 |
| Alembic init + async env.py | Task 4 |
| Agents directory stubs with typed signatures | Task 5 |
| scratchpad.md | Task 10 |

Constraints respected:
- No route logic, model logic, or agent logic — only stubs and structure
- pyproject.toml only — no requirements.txt
- No packages beyond the listed 14 deps
- No database migration (Task 4 sets up Alembic but does NOT run `alembic revision`)
- No class components, no Redux/Zustand
