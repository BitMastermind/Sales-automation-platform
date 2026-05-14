# 01 — Build Phases

The project is built in **8 phases (0 → 7)**. Each phase is one session with Claude Code. Do not start Phase N+1 until Phase N's verification command passes and `CLAUDE.md`'s Current Status is updated.

| Phase | Theme | Output |
|-------|-------|--------|
| 0 | Project scaffold | All folders, env, Docker skeleton, Makefile |
| 1 | Data layer | Postgres schema + Alembic + Qdrant collections |
| 2 | FastAPI backend | API routes + Gmail OAuth |
| 3 | LangGraph agents | Research, Personalization, Compliance, Reply, Follow-up |
| 4 | n8n workflows | Launcher, reply monitor, follow-up scheduler |
| 5 | Next.js frontend | Dashboard, campaign creation, lead detail |
| 6 | Integration tests | End-to-end pytest suite |
| 7 | Docker & deploy | Full `docker compose up` |

---

## Phase 0 — Project Scaffold

**Goal:** Directory structure, tooling, env config. No business logic yet.

**Tasks**
1. `npx create-next-app@latest frontend --typescript --tailwind --app --src-dir`
2. Init FastAPI in `/backend` with `pyproject.toml` (not `requirements.txt`); folders: `api/ core/ models/ services/ agents_interface/ tests/`.
3. `.env.example` with all keys (see [CLAUDE.md](../CLAUDE.md#environment-variables)).
4. Docker Compose skeleton with health checks for postgres, qdrant, redis, n8n.
5. Root `Makefile`: `dev`, `test`, `migrate`, `lint`, `seed`.

**Verify:** `docker compose config` parses without errors.

---

## Phase 1 — Data Layer

### 1A. PostgreSQL
**Location:** `/backend/models/`

Tables (SQLAlchemy 2.0 async ORM):
- `campaigns` (id, name, status, created_at, settings JSONB)
- `leads` (id, campaign_id FK, company_name, website, contact_name, email, status enum, research_data JSONB, created_at)
- `emails` (id, lead_id FK, subject, body, sent_at, opened_at, replied_at, type enum)
- `replies` (id, email_id FK, content, classified_as enum, received_at)
- `crm_updates` (id, lead_id FK, platform, payload JSONB, synced_at)
- `oauth_tokens` (id, user_id, provider, access_token_enc, refresh_token_enc, expires_at)

Rules: UUID PKs, UTC timestamps, indexes on `leads.email`, `leads.campaign_id`, `emails.lead_id`.

**Verify:** `alembic revision --autogenerate -m "initial_schema"` then `alembic upgrade head`.

### 1B. Qdrant
**Location:** `/backend/core/vector_store.py`

Collections:
- `company_research` — vector size 1536 (`text-embedding-3-small`); payload: `company_name, website, lead_id, research_summary, timestamp`
- `email_templates` — vector size 1536; payload: `industry, pain_point, email_body, reply_rate`

Expose `VectorStoreClient` with: `upsert_company_research`, `search_similar_companies`, `upsert_email_template`, `get_best_templates`.

**Verify:** `pytest backend/tests/test_vector_store.py -v`.

---

## Phase 2 — FastAPI Backend

### 2A. Routes
**Location:** `/backend/api/`

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/campaigns` | Create campaign |
| GET | `/api/campaigns` | List (paginated) |
| GET | `/api/campaigns/{id}` | Detail + stats |
| PATCH | `/api/campaigns/{id}/status` | draft / active / paused / completed |
| POST | `/api/leads/upload` | CSV upload, parse, validate, bulk-insert |
| GET | `/api/leads?campaign_id=` | List leads |
| GET | `/api/leads/{id}` | Lead detail + email history |
| GET | `/api/emails?lead_id=` | Email history |
| POST | `/api/emails/{id}/resend` | Trigger resend |
| POST | `/api/webhooks/n8n/reply-received` | Reply ingestion |
| POST | `/api/webhooks/n8n/email-opened` | Tracking pixel |

Response shape: `{ "data": ..., "error": null, "meta": {...} }`.
Middleware: request/response logging, CORS for `localhost:3000`.

**Verify:** `pytest backend/tests/ -v`.

### 2B. Gmail OAuth
**Location:** `/backend/services/gmail_service.py`

- Scopes: `gmail.send`, `gmail.readonly`.
- Tokens stored encrypted in `oauth_tokens` table.
- Auto-refresh on expiry.
- Class methods: `get_auth_url`, `exchange_code`, `send_email`, `create_draft`, `list_recent_replies`.
- Rate limit: 100 emails/day per account, counter in Redis.

Routes: `GET /api/auth/gmail`, `GET /api/auth/gmail/callback`.

**Verify:** mock-Gmail test suite passes; OAuth flow round-trips locally.

---

## Phase 3 — LangGraph Agents

Each agent: own file in `/agents/`, single async entry point, Pydantic state.

### 3A. Research Agent — `agents/research_agent.py`
Nodes: `fetch_website → search_news → extract_tech_stack → synthesize → check_quality`.
Loop back to `synthesize` if `research_summary < 50 words`.
Synthesis: Claude `claude-sonnet-4-20250514`. Quality check: `gpt-4o-mini`.

### 3B. Personalization Agent — `agents/personalization_agent.py`
Nodes: `retrieve_templates → draft_email → compliance_check → refine`.
Compliance fails → up to 2 refines.
Avoid: `guaranteed, free money, act now, limited time, click here`.

### 3C. Follow-up Agent — `agents/followup_agent.py`
Day 3 = short bump; Day 7 = value-add; Day 14 = break-up; Day >14 = `{should_send: false}`.
Reads prior follow-ups from DB to avoid repeating angles.

Full specs (state schemas, prompts, edges): [03-AGENTS.md](03-AGENTS.md)

**Verify:** integration tests in `/backend/tests/integration/test_agents_*.py` pass with mocked LLMs.

---

## Phase 4 — n8n Workflows

**Location:** `/n8n-workflows/`

- `campaign_launcher.json` — webhook → per-lead research + email, 30s rate limit between leads
- `gmail_reply_monitor.json` — cron 15 min → search Gmail → webhook FastAPI → Slack
- `followup_scheduler.json` — cron daily 09:00 → fetch follow-up candidates → trigger → Sheets log

**Verify:** import into n8n locally, fire each manually, see expected side-effects.

---

## Phase 5 — Frontend

### 5A. Dashboard layout
Pages: `/dashboard`, `/campaigns`, `/campaigns/[id]`, `/settings`.
Components from shadcn/ui. Charts via Recharts.
Data via TanStack Query. **No** Redux/Zustand.

### 5B. Campaign creation
Three-step form (React state machine — no form library):
1. Basics (name, product, value prop, case study)
2. Lead upload (react-dropzone, preview, column mapping, validation)
3. Review & launch

**Verify:** create a campaign in the UI, see it in `/campaigns`.

---

## Phase 6 — Integration Tests

**Location:** `/backend/tests/integration/`

| Test | Asserts |
|------|---------|
| `test_campaign_creation` | POST returns 201, row in DB |
| `test_lead_upload` | CSV ingested, leads count matches |
| `test_research_agent_mock` | Structured output schema valid |
| `test_personalization_agent_mock` | Email present, < 200 words, no spam words |
| `test_webhook_reply` | Reply persisted, lead status updated |

Use `pytest-asyncio`, `respx`, `factory-boy`. **Real Postgres** in test container — no DB mocks.

**Verify:** `pytest backend/tests/integration/ -v` — 5/5 pass.

---

## Phase 7 — Docker & Deployment

**Location:** `/infra/docker-compose.yml`

Services: postgres, qdrant, redis, n8n, backend, frontend (each healthy).
Dockerfiles: multi-stage, non-root user.
Makefile: `dev`, `migrate`, `test`, `seed`.

**Verify:** `docker compose up --build` → all services `healthy`; visit `localhost:3000`, create a campaign end-to-end.

---

## After Each Phase
1. Update **Current Status** in [CLAUDE.md](../CLAUDE.md).
2. Append a 3-line summary of what shipped + any surprises to `scratchpad.md`.
3. Commit. Start the next phase in a fresh Claude Code session.
