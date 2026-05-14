# Phases 6 & 7 — Integration Tests + Docker Deployment

> Two sessions. Phase 6 is about proving correctness end-to-end. Phase 7 is about shipping it.

---

## Phase 6 — Integration Tests

| | |
|---|---|
| **Model** | `claude-sonnet-4-6` |
| **Skills** | Invoke `verification-before-completion` before claiming any test suite passes |
| **Depends on** | Phases 1–5 complete. Backend runs locally. |
| **Rule** | Real Postgres test container — NO database mocking. |

### Prompt

```
Read CLAUDE.md before starting.

## Context
Phase 6: end-to-end integration test suite for the critical path.
These tests run against a real Postgres instance (use a test database, not production).
All external APIs (Tavily, Firecrawl, OpenAI, Gmail) are mocked with respx.
LangGraph agents are mocked at the agents_interface layer — we are testing the full
backend request path, not the agent internals (those have their own unit tests).

## Setup Requirements
Add to pyproject.toml (if not already there):
  pytest-asyncio, respx, factory-boy, pytest-cov

Add /backend/tests/integration/conftest.py:
  - Create a separate test database: postgres://sales:sales@localhost:5432/sales_test
  - Run Alembic migrations against it at the start of the test session.
  - Provide an async_session fixture scoped to function (rollback after each test).
  - Provide an async_client fixture: httpx.AsyncClient(app=app, base_url="http://test")
  - Do NOT mock the DB — the fixture uses a real Postgres connection.

## Task: Write 5 integration tests

### Test 1 — test_campaign_creation.py
Scenario: User creates a campaign via the API.
  1. POST /api/campaigns with valid CampaignCreate data.
  2. Assert response is 201.
  3. Assert response body has id, name, status="draft".
  4. Query the DB directly: assert Campaign row exists with the correct name.
  5. GET /api/campaigns/{id} → assert stats are all 0.

### Test 2 — test_lead_upload.py
Scenario: User uploads a 3-lead CSV with one invalid email.
  Setup: Create a campaign in the DB (use factory-boy CampaignFactory).
  
  Create a test CSV file in memory:
    company_name,email,website,contact_name
    Acme Corp,john@acme.com,acme.com,John
    Beta Inc,jane@beta.com,beta.com,Jane
    Bad Lead,not-an-email,,
  
  1. POST /api/leads/upload (multipart) with the CSV + campaign_id.
  2. Assert response: { data: { inserted: 2, skipped: 1, errors: [{ row: 3, reason: "invalid email" }] } }
  3. Query DB: assert exactly 2 Lead rows for this campaign.
  4. Assert the valid leads have status="new".
  5. GET /api/leads?campaign_id={id} → assert 2 results.

### Test 3 — test_research_agent_mock.py
Scenario: Internal trigger-research endpoint runs the research agent and saves to DB.
  Setup:
    - Create Campaign + Lead in DB.
    - Mock agents_interface.research.trigger_research to return a fixed research dict:
      { industry: "SaaS", company_size: "100", pain_points: ["manual ops"],
        recent_news: [], tech_stack: ["Salesforce"], research_summary: "Acme is a SaaS company." }
    
  1. POST /api/internal/trigger-research with { lead_id: lead.id }
     Include header: X-Internal-Token: <INTERNAL_API_TOKEN from settings>
  2. Assert response: { data: { queued: true, lead_id: ... } }
  3. Query DB: lead.research_data is not null.
  4. Assert lead.status = "researched".
  5. Assert the research_data JSON contains all expected keys.
  
  Also test auth:
  6. POST same endpoint WITHOUT the X-Internal-Token header → assert 401.

### Test 4 — test_personalization_agent_mock.py
Scenario: Trigger-personalization creates an email row in the DB.
  Setup:
    - Create Campaign + Lead (with research_data already set) in DB.
    - Mock agents_interface.personalization.trigger_personalization to return:
      { subject: "Quick question", opening_line: "Saw your recent expansion...",
        body: "...(100 words)...", cta: "Open to a quick call?",
        full_email: "Quick question\n\nSaw your recent expansion...\n\n...(100 words)...\n\nOpen to a quick call?",
        lead_email: lead.email }
  
  1. POST /api/internal/trigger-personalization with { lead_id: lead.id }
  2. Assert 200.
  3. Query DB: assert 1 Email row for this lead, type="outreach".
  4. Assert email.subject = "Quick question".
  5. Count words in email.body — assert < 200.
  6. Check no spam words: assert none of ["guaranteed", "free money", "act now"] in email.body.lower().

### Test 5 — test_webhook_reply.py
Scenario: n8n delivers a reply; it is persisted and classified.
  Setup:
    - Create Campaign + Lead + Email (with gmail_message_id = "abc123") in DB.
    - Mock agents_interface.classifier.classify_reply to return:
      ClassificationResult(intent="interested", confidence=0.9,
        suggested_next_action="schedule_call", key_phrases=["sounds great"])
  
  1. POST /api/webhooks/n8n/reply-received:
     { "gmail_message_id": "abc123", "reply_text": "Sounds great, let's talk!", "received_at": "2026-05-14T10:00:00Z" }
  2. Assert 200.
  3. Assert response: { data: { reply_id: <uuid>, classified_as: "interested" } }
  4. Query DB: Reply row exists with classified_as="interested".
  5. Query DB: Lead.status = "meeting_booked".
  6. Query DB: Email.replied_at is not null.
  
  Also test unknown gmail_message_id:
  7. POST same endpoint with gmail_message_id = "unknown999" → assert 404.

### Test 6 — test_followup_candidates.py (bonus)
Scenario: leads-needing-followup returns the right leads.
  Setup: Create 3 leads with different email sent_at values:
    Lead A: email sent 3 days ago (no reply)
    Lead B: email sent 7 days ago (no reply)
    Lead C: email sent 7 days ago (HAS a reply)
    Lead D: email sent 1 day ago (no reply)
  
  1. GET /api/internal/leads-needing-followup (with X-Internal-Token header)
  2. Assert 2 results (Lead A and Lead B — not C which has a reply, not D which is too recent).
  3. Assert Lead A has days_since_sent ≈ 3.

## Factories (create /backend/tests/factories.py)
Using factory-boy + SQLAlchemy:
  class CampaignFactory(AsyncSQLAlchemyModelFactory):
      class Meta:
          model = Campaign
      name = factory.Faker("company")
      status = "draft"
      settings = factory.LazyFunction(lambda: {...})

  class LeadFactory(AsyncSQLAlchemyModelFactory):
      class Meta:
          model = Lead
      company_name = factory.Faker("company")
      email = factory.Faker("email")
      status = "new"
      campaign_id = factory.SubFactory(CampaignFactory)

  class EmailFactory(AsyncSQLAlchemyModelFactory):
      ...

## Coverage target
Run: pytest backend/tests/integration/ -v --cov=backend/api --cov-report=term-missing
Target: > 80% coverage on /backend/api/ (routers).

## Constraints
- Tests use a real Postgres database — no sqlite, no mocking the DB session.
- Each test must be fully isolated (rollback fixture).
- Do NOT test agent internals here — only the HTTP request path.
- Do NOT add test-only code to production modules.

## Verify
Run: pytest backend/tests/integration/ -v
Expected: 6 tests (or 5 + 1 bonus), all pass.

Run: pytest backend/tests/ -v (the full suite including unit tests)
Expected: All tests pass. Zero failures.

Report: pytest ... --tb=short > test_results.txt and paste the last 20 lines into scratchpad.md.
```

---

## Phase 7 — Docker & Deployment

| | |
|---|---|
| **Model** | `claude-sonnet-4-6` |
| **Skills** | Invoke `verification-before-completion` before claiming the stack is healthy |
| **Depends on** | Phase 6 complete (all tests pass) |

### Prompt

```
Read CLAUDE.md before starting.

## Context
Phase 7: finalize the Docker Compose setup so the entire system runs with `make dev`.
Each service must reach a "healthy" state. The Makefile must have working commands.
This is the final phase — after this, the system is demo-ready.

## Task

### Step 1 — /backend/Dockerfile (multi-stage)
Stage 1 (builder):
  FROM python:3.11-slim as builder
  WORKDIR /app
  COPY pyproject.toml .
  RUN pip install --no-cache-dir --prefix=/install .

Stage 2 (runtime):
  FROM python:3.11-slim
  RUN useradd --create-home appuser
  COPY --from=builder /install /usr/local
  COPY . /app
  WORKDIR /app
  USER appuser
  EXPOSE 8000
  CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

/backend/.dockerignore:
  __pycache__, .venv, .pytest_cache, *.pyc, alembic/versions/*.py (keep only the latest)
  .env, .env.*

### Step 2 — /frontend/Dockerfile (multi-stage)
Stage 1 (deps):
  FROM node:20-alpine as deps
  WORKDIR /app
  COPY package.json package-lock.json ./
  RUN npm ci

Stage 2 (builder):
  FROM node:20-alpine as builder
  WORKDIR /app
  COPY --from=deps /app/node_modules ./node_modules
  COPY . .
  RUN npm run build

Stage 3 (runner):
  FROM node:20-alpine as runner
  RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs
  COPY --from=builder /app/.next/standalone ./
  COPY --from=builder /app/.next/static ./.next/static
  USER nextjs
  EXPOSE 3000
  CMD ["node", "server.js"]

Add to /frontend/next.config.js: output: 'standalone'

/frontend/.dockerignore:
  node_modules, .next, .env*

### Step 3 — /infra/docker-compose.yml (complete version)
Fill in the full compose file (scaffolded in Phase 0, now complete):

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: sales
      POSTGRES_PASSWORD: sales
      POSTGRES_DB: sales
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U sales"]
      interval: 5s
      timeout: 5s
      retries: 5

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrantdata:/qdrant/storage
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:6333/healthz || exit 1"]
      interval: 10s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      retries: 5

  n8n:
    image: n8nio/n8n:latest
    ports:
      - "5678:5678"
    environment:
      - N8N_HOST=0.0.0.0
      - WEBHOOK_URL=${N8N_WEBHOOK_URL}
    volumes:
      - n8ndata:/home/node/.n8n
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:5678/healthz || exit 1"]
      interval: 15s
      retries: 5

  backend:
    build:
      context: ../backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ../backend:/app
    env_file:
      - ../.env
    depends_on:
      postgres:
        condition: service_healthy
      qdrant:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:8000/health || exit 1"]
      interval: 10s
      retries: 5

  frontend:
    build:
      context: ../frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    volumes:
      - ../frontend/src:/app/src   # hot reload for dev
    environment:
      - NEXT_PUBLIC_API_BASE=http://localhost:8000
    depends_on:
      - backend

networks:
  default:
    name: saleshq

volumes:
  pgdata:
  qdrantdata:
  redisdata:
  n8ndata:

### Step 4 — Root Makefile (complete)
.PHONY: dev migrate test lint seed

dev:
	docker compose -f infra/docker-compose.yml up --build

migrate:
	docker compose -f infra/docker-compose.yml exec backend alembic upgrade head

test:
	docker compose -f infra/docker-compose.yml exec backend pytest -v

lint:
	docker compose -f infra/docker-compose.yml exec backend ruff check .
	docker compose -f infra/docker-compose.yml exec backend mypy . --ignore-missing-imports
	docker compose -f infra/docker-compose.yml exec frontend npm run lint

seed:
	docker compose -f infra/docker-compose.yml exec backend python scripts/seed.py

logs:
	docker compose -f infra/docker-compose.yml logs -f backend frontend

stop:
	docker compose -f infra/docker-compose.yml down

reset:
	docker compose -f infra/docker-compose.yml down -v

### Step 5 — Seed script: /backend/scripts/seed.py
Create a script that:
  1. Connects to the DB.
  2. Creates 1 campaign: "Demo Campaign — AI for SaaS" (status=active).
  3. Creates 3 leads:
     - Stripe, stripe.com, john@stripe.com, John Collison
     - Notion, notion.so, jane@notion.so, Jane Smith  
     - Linear, linear.app, alex@linear.app, Alex Karev
  4. For each lead: inserts a fake email (type=outreach, subject, body) with sent_at = now().
  5. Prints: "Seed complete. 1 campaign, 3 leads, 3 emails inserted."

### Step 6 — /backend/main.py — add /health and startup event
  @app.get("/health")
  async def health():
      return {"status": "ok", "version": "1.0.0"}

  @app.on_event("startup")
  async def startup():
      # Run async DB table creation check (not migration — Alembic handles that)
      # Log: "Backend started"

### Step 7 — Final cleanup
  - Ensure all .env.example keys are present in docker-compose.yml (passed via env_file or environment).
  - Remove any TODO comments or placeholder stubs left from earlier phases.
  - Run ruff format . in /backend to enforce code style.
  - Run cd frontend && npx next lint.

## Constraints
- Dockerfiles must use non-root users — never run as root in containers.
- The backend container must use the /health endpoint (not ping) for its healthcheck.
- The seed script must be idempotent: if run twice, it should not error or create duplicate data.
- The reset Makefile target (docker compose down -v) is destructive — it wipes volumes.
  Keep it in the Makefile but add a comment: "WARNING: destroys all data".

## Verify
Step 1: cp .env.example .env → fill in OPENAI_API_KEY, ANTHROPIC_API_KEY at minimum.
Step 2: make dev (wait for all services to become healthy — takes ~60 seconds)
Step 3: docker compose ps → all services show "(healthy)"
Step 4: make migrate → "Running upgrade ... initial_schema" (or "already at head")
Step 5: make seed → "Seed complete. 1 campaign, 3 leads, 3 emails inserted."
Step 6: Open http://localhost:3000 → dashboard loads with stat cards.
Step 7: Open http://localhost:3000/campaigns → 1 campaign listed.
Step 8: Click the campaign → 3 leads listed with status "email_sent".
Step 9: http://localhost:8000/docs → FastAPI Swagger UI loads.
Step 10: http://localhost:5678 → n8n UI loads.

All 10 checks must pass.

Update CLAUDE.md: Phase 7 → ✅ complete.
Append final note to scratchpad.md: total build time, any port conflicts, Docker oddities.
```

---

## After Phase 7
1. Run all 10 verification steps.
2. Take a screenshot of the full stack running.
3. Update CLAUDE.md: all phases ✅ complete.
4. Final commit: `git commit -m "Phase 7 complete: full stack deployable via docker compose"`
5. Optionally: run `/skill finishing-a-development-branch` for merge/PR options.
