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

---

#### ROLE & PERSONA

You are a senior backend engineer specializing in integration testing for FastAPI + PostgreSQL systems. You have built test suites using real databases, factory-boy, and respx mocks, and you understand the difference between testing the HTTP request path and testing agent internals.

---

#### TASK & OBJECTIVE

Write 6 integration tests (5 required + 1 bonus) that exercise the critical request paths against a real Postgres test database — covering campaign creation, lead CSV upload, research/personalization agent triggers (mocked at the interface layer), webhook reply processing, and follow-up candidate selection — achieving > 80% route coverage.

---

#### MY SITUATION

Phases 1–5 are complete. The FastAPI app runs with all routes implemented. The `agents_interface` layer has real implementations (Phase 3). A test database `sales_test` can be created on the same Postgres instance. `pytest-asyncio`, `respx`, `factory-boy`, and `httpx` are in `pyproject.toml`. `pytest-cov` needs to be added if not already present.

---

#### CONSTRAINTS

- **Real Postgres** — no SQLite, no mocking the DB session, no `@pytest.mark.skip` on DB-dependent tests.
- **Each test is fully isolated** — use a rollback fixture scoped to function.
- **Do not test agent internals here** — mock at the `agents_interface` layer only. Agent unit tests exist from Phase 3.
- **Do not add test-only code to production modules** — use monkeypatching or dependency injection.
- X-Internal-Token must be present on all `/api/internal/*` requests — test 401 path too.

---

#### AUDIENCE FOR THE OUTPUT

This test suite is the final correctness gate before Phase 7 deployment. It runs in CI and in `make test` inside Docker. The output is also pasted into `scratchpad.md` as a record. Any flaky test (passes sometimes, fails others) is worse than no test — make each test deterministic.

---

#### PRIOR ATTEMPTS / WHAT FAILED

- Do not use `async with AsyncClient(app=app)` without setting `base_url` — it will raise on relative URLs.
- Do not use `factory.Faker("email")` and then try to look up the lead by that email — Faker generates non-deterministic values; store the created object and use its `.id`.
- Do not use `datetime.now()` in tests without timezone — all timestamps are UTC in this project.
- Do not run tests against the production database by accident — always override `DATABASE_URL` in the test conftest to point at `sales_test`.

---

#### FORMAT

Deliver files in this order:
1. `pyproject.toml` addition — `pytest-cov` if missing
2. `/backend/tests/factories.py` — `CampaignFactory`, `LeadFactory`, `EmailFactory`
3. `/backend/tests/integration/conftest.py` — test DB setup, rollback fixture, `async_client` fixture
4. `/backend/tests/integration/test_campaign_creation.py`
5. `/backend/tests/integration/test_lead_upload.py`
6. `/backend/tests/integration/test_research_agent_mock.py`
7. `/backend/tests/integration/test_personalization_agent_mock.py`
8. `/backend/tests/integration/test_webhook_reply.py`
9. `/backend/tests/integration/test_followup_candidates.py` (bonus)
10. Verify commands + expected output.

---

#### TONE & EXPERTISE LEVEL

Expert. pytest-asyncio, httpx.AsyncClient, factory-boy async, and SQLAlchemy async session patterns assumed known.

---

#### THINKING INSTRUCTION

Before writing `conftest.py`, think through the rollback isolation strategy: does the rollback happen at the session level or transaction level? How does `httpx.AsyncClient` share the same DB session as the route handler when the app creates its own session per request? State the isolation approach before writing the fixture — this is the highest-risk part of the test setup.

---

#### DETAILED SPEC

**`/backend/tests/integration/conftest.py`:**
- Override `DATABASE_URL` to `sales_test`.
- Run Alembic migrations once per test session (`session` scope).
- `async_session` fixture: `function` scope, rollback after each test.
- `async_client` fixture: `httpx.AsyncClient(app=app, base_url="http://test")`.

**`/backend/tests/factories.py`** — factory-boy + SQLAlchemy:
```python
class CampaignFactory(AsyncSQLAlchemyModelFactory):
    class Meta: model = Campaign
    name = factory.Faker("company")
    status = "draft"
    settings = factory.LazyFunction(lambda: { ... })

class LeadFactory(AsyncSQLAlchemyModelFactory):
    class Meta: model = Lead
    company_name = factory.Faker("company")
    email = factory.Faker("email")
    status = "new"
    campaign_id = factory.SubFactory(CampaignFactory)

class EmailFactory(AsyncSQLAlchemyModelFactory):
    class Meta: model = Email
    # type, subject, body, lead_id
```

---

**Test 1 — `test_campaign_creation.py`:**
1. `POST /api/campaigns` with valid `CampaignCreate` data → assert 201.
2. Assert response body has `id`, `name`, `status="draft"`.
3. Query DB directly → assert Campaign row exists with correct name.
4. `GET /api/campaigns/{id}` → assert all stats are 0.

**Test 2 — `test_lead_upload.py`:**

Setup: `CampaignFactory` in DB.

In-memory CSV:
```
company_name,email,website,contact_name
Acme Corp,john@acme.com,acme.com,John
Beta Inc,jane@beta.com,beta.com,Jane
Bad Lead,not-an-email,,
```

1. `POST /api/leads/upload` (multipart) with CSV + `campaign_id`.
2. Assert response: `{ "inserted": 2, "skipped": 1, "errors": [{ "row": 3, "reason": "invalid email" }] }`.
3. Query DB → assert exactly 2 Lead rows for this campaign.
4. Assert valid leads have `status="new"`.
5. `GET /api/leads?campaign_id={id}` → assert 2 results.

**Test 3 — `test_research_agent_mock.py`:**

Setup: Campaign + Lead in DB. Mock `agents_interface.research.trigger_research` to return:
```python
{ "industry": "SaaS", "company_size": "100", "pain_points": ["manual ops"],
  "recent_news": [], "tech_stack": ["Salesforce"], "research_summary": "Acme is a SaaS company." }
```

1. `POST /api/internal/trigger-research` with `{ "lead_id": lead.id }` + `X-Internal-Token` header.
2. Assert `{ "data": { "queued": true, "lead_id": ... } }`.
3. Query DB → `lead.research_data` is not null.
4. Assert `lead.status = "researched"`.
5. Assert `research_data` JSON contains all expected keys.
6. Repeat without `X-Internal-Token` → assert 401.

**Test 4 — `test_personalization_agent_mock.py`:**

Setup: Campaign + Lead (with `research_data`) in DB. Mock `agents_interface.personalization.trigger_personalization` to return:
```python
{ "subject": "Quick question",
  "opening_line": "Saw your recent expansion...",
  "body": "...(100 words)...",
  "cta": "Open to a quick call?",
  "full_email": "Quick question\n\nSaw your recent expansion...\n\n...\n\nOpen to a quick call?",
  "lead_email": lead.email }
```

1. `POST /api/internal/trigger-personalization` with `{ "lead_id": lead.id }` → assert 200.
2. Query DB → assert 1 Email row, `type="outreach"`.
3. Assert `email.subject = "Quick question"`.
4. Assert `len(email.body.split()) < 200`.
5. Assert none of `["guaranteed", "free money", "act now"]` in `email.body.lower()`.

**Test 5 — `test_webhook_reply.py`:**

Setup: Campaign + Lead + Email (with `gmail_message_id="abc123"`) in DB. Mock `agents_interface.classifier.classify_reply` to return:
```python
ClassificationResult(intent="interested", confidence=0.9,
    suggested_next_action="schedule_call", key_phrases=["sounds great"])
```

1. `POST /api/webhooks/n8n/reply-received`: `{ "gmail_message_id": "abc123", "reply_text": "Sounds great, let's talk!", "received_at": "2026-05-14T10:00:00Z" }`.
2. Assert 200 and `{ "data": { "reply_id": <uuid>, "classified_as": "interested" } }`.
3. Query DB → Reply row exists with `classified_as="interested"`.
4. Query DB → `Lead.status = "meeting_booked"`.
5. Query DB → `Email.replied_at` is not null.
6. Repeat with `gmail_message_id="unknown999"` → assert 404.

**Test 6 — `test_followup_candidates.py` (bonus):**

Setup: 4 leads with emails at different sent_at values:
- Lead A: sent 3 days ago, no reply
- Lead B: sent 7 days ago, no reply
- Lead C: sent 7 days ago, has a Reply row
- Lead D: sent 1 day ago, no reply

1. `GET /api/internal/leads-needing-followup` with `X-Internal-Token`.
2. Assert 2 results (Lead A and Lead B only).
3. Assert Lead A has `days_since_sent ≈ 3`.

**Coverage target:**
```bash
pytest backend/tests/integration/ -v --cov=backend/api --cov-report=term-missing
# Target: > 80% on /backend/api/ routers
```

**Verify:**
```bash
pytest backend/tests/integration/ -v
# Expected: 6 tests (or 5 + 1 bonus), all pass

pytest backend/tests/ -v
# Expected: All tests pass (unit + integration). Zero failures.

pytest backend/tests/ -v --tb=short > test_results.txt
# Paste last 20 lines into scratchpad.md
```

---

## Phase 7 — Docker & Deployment

| | |
|---|---|
| **Model** | `claude-sonnet-4-6` |
| **Skills** | Invoke `verification-before-completion` before claiming the stack is healthy |
| **Depends on** | Phase 6 complete (all tests pass) |

---

#### ROLE & PERSONA

You are a senior DevOps engineer with deep experience in multi-service Docker Compose deployments, multi-stage Docker builds, and production healthcheck configuration. You have shipped Next.js + FastAPI stacks with non-root container users and proper dependency ordering.

---

#### TASK & OBJECTIVE

Finalize the Docker Compose stack so `make dev` brings up all 6 services to a healthy state, add multi-stage Dockerfiles for backend and frontend, write a seed script, and pass all 10 manual verification checks — making the system demo-ready.

---

#### MY SITUATION

Phase 6 is complete — all tests pass. The Phase 0 Docker Compose and Makefiles are stubs. `/backend/Dockerfile` and `/frontend/Dockerfile` do not exist yet. The backend `main.py` has a `/health` route. The `next.config.js` does not yet set `output: 'standalone'`.

---

#### CONSTRAINTS

- **Dockerfiles must use non-root users** — never run processes as root in containers.
- **The backend healthcheck must use `/health`**, not `ping` or port checks.
- **The seed script must be idempotent** — running it twice must not create duplicate data or error.
- **The `reset` Makefile target is destructive** — add a prominent `WARNING: destroys all data` comment.
- **No `.env` or `.env.*` files in Docker images** — use `env_file` in `docker-compose.yml` only.
- Do not commit `alembic/versions/` intermediate files to the backend image — only the latest migration.

---

#### AUDIENCE FOR THE OUTPUT

This is the deployment artifact used by: the solo operator running `make dev` locally, and the CI/CD pipeline running `make test` + `make migrate`. The `docker compose ps` output showing all services `(healthy)` is the demo-ready proof.

---

#### PRIOR ATTEMPTS / WHAT FAILED

- Do not use `RUN pip install -r requirements.txt` — this project uses `pyproject.toml`.
- Do not mount `/app` as a volume in production mode — hot-reload volumes are for development only (already scoped in the compose file).
- Do not use `depends_on: service_name` (simple form) — use `condition: service_healthy` for all hard dependencies (postgres, qdrant, redis → backend).
- Do not forget `output: 'standalone'` in `next.config.js` — the frontend Dockerfile runner stage requires it.
- The `@app.on_event("startup")` decorator is deprecated in FastAPI 0.115+ — use the `lifespan` context manager pattern instead.

---

#### FORMAT

Deliver files in this order:
1. `/backend/Dockerfile` — multi-stage (builder + runtime)
2. `/backend/.dockerignore`
3. `/frontend/Dockerfile` — multi-stage (deps + builder + runner)
4. `/frontend/.dockerignore`
5. `/frontend/next.config.js` addition — `output: 'standalone'`
6. `/infra/docker-compose.yml` — complete with all 6 services + healthchecks
7. `Makefile` (root) — all 7 targets
8. `/backend/scripts/seed.py` — idempotent seed script
9. `/backend/main.py` update — `/health` + lifespan startup
10. Final cleanup checklist
11. Verify steps (10 manual checks).

---

#### TONE & EXPERTISE LEVEL

Expert. Docker multi-stage builds, Docker Compose `condition: service_healthy`, and FastAPI lifespan patterns assumed known.

---

#### THINKING INSTRUCTION

Before writing `docker-compose.yml`, verify the dependency chain: which services must be healthy before `backend` starts? Which must be healthy before `frontend` starts? Draw the dependency graph in a comment in the compose file. Then verify that every service with a healthcheck has its `interval`, `timeout`, and `retries` set conservatively enough to survive a cold Docker pull on first run.

---

#### DETAILED SPEC

**`/backend/Dockerfile`** — multi-stage:
```dockerfile
# Stage 1: builder
FROM python:3.11-slim as builder
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir --prefix=/install .

# Stage 2: runtime
FROM python:3.11-slim
RUN useradd --create-home appuser
COPY --from=builder /install /usr/local
COPY . /app
WORKDIR /app
USER appuser
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

**`/backend/.dockerignore`:** `__pycache__`, `.venv`, `.pytest_cache`, `*.pyc`, `.env`, `.env.*`

**`/frontend/Dockerfile`** — multi-stage:
```dockerfile
FROM node:20-alpine as deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-alpine as builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine as runner
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
```

**`/infra/docker-compose.yml`** — 6 services:

| Service | Image | Ports | Healthcheck |
|---------|-------|-------|-------------|
| postgres | postgres:15 | — | `pg_isready -U sales`, interval 5s, retries 5 |
| qdrant | qdrant/qdrant:latest | 6333:6333 | `curl -sf http://localhost:6333/healthz`, interval 10s |
| redis | redis:7-alpine | — | `redis-cli ping`, interval 5s |
| n8n | n8nio/n8n:latest | 5678:5678 | `curl -sf http://localhost:5678/healthz`, interval 15s |
| backend | build: ../backend | 8000:8000 | `curl -sf http://localhost:8000/health`, interval 10s |
| frontend | build: ../frontend | 3000:3000 | — |

`backend` depends_on: postgres, qdrant, redis — all `condition: service_healthy`.
`frontend` depends_on: backend (simple — no healthcheck needed).
Network name: `saleshq`. Volumes: `pgdata`, `qdrantdata`, `redisdata`, `n8ndata`.

**Root Makefile targets:** `dev`, `migrate`, `test`, `lint`, `seed`, `logs`, `stop`, `reset`.
`reset` comment: `# WARNING: destroys all data (volumes)`.

**`/backend/scripts/seed.py`** — idempotent:
1. Connect to DB.
2. Upsert 1 campaign: "Demo Campaign — AI for SaaS" (status=active). Skip if exists.
3. Upsert 3 leads: Stripe/stripe.com, Notion/notion.so, Linear/linear.app. Skip if email already exists.
4. For each lead: insert 1 outreach email (sent_at=now) if no email exists yet.
5. Print: "Seed complete. 1 campaign, 3 leads, 3 emails inserted." (or "already seeded" per entity).

**`/backend/main.py`** additions:
```python
# Use lifespan pattern (not deprecated @app.on_event):
@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("Backend started")
    yield

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
```

**Final cleanup checklist:**
- All `.env.example` keys present in `docker-compose.yml` (via `env_file` or `environment`).
- Remove any TODO comments or `NotImplementedError` stubs left from earlier phases.
- Run `ruff format .` in `/backend`.
- Run `cd frontend && npx next lint`.

**Verify (all 10 must pass):**
```bash
# 1. cp .env.example .env  (fill in OPENAI_API_KEY, ANTHROPIC_API_KEY at minimum)
# 2. make dev  (wait ~60s for all services to become healthy)
# 3. docker compose ps  → all services show "(healthy)"
# 4. make migrate  → "Running upgrade ... initial_schema" (or "already at head")
# 5. make seed  → "Seed complete. 1 campaign, 3 leads, 3 emails inserted."
# 6. Open http://localhost:3000  → dashboard loads with stat cards
# 7. Open http://localhost:3000/campaigns  → 1 campaign listed
# 8. Click the campaign  → 3 leads listed with status "email_sent"
# 9. Open http://localhost:8000/docs  → FastAPI Swagger UI loads
# 10. Open http://localhost:5678  → n8n UI loads
```

Update `CLAUDE.md`: Phase 7 → ✅ complete.
Append to `scratchpad.md`: total build time, any port conflicts, Docker oddities.

---

## After Phase 7

1. Run all 10 verification steps.
2. Take a screenshot of the full stack running.
3. Update `CLAUDE.md`: all phases ✅ complete.
4. Final commit: `git commit -m "Phase 7 complete: full stack deployable via docker compose"`.
5. Optionally: run `/skill finishing-a-development-branch` for merge/PR options.
