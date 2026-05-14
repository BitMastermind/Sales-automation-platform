# Phases 1 & 2 — Data Layer + FastAPI Backend

> Two separate sessions. Finish and verify Phase 1 before opening Phase 2.

---

## Phase 1A — PostgreSQL Schema

| | |
|---|---|
| **Model** | `claude-sonnet-4-6` |
| **Skills** | Invoke `test-driven-development` before starting |
| **Depends on** | Phase 0 complete (`docker compose -f infra/docker-compose.yml config` passes) |

### Prompt

---

#### ROLE & PERSONA

You are a senior Python backend engineer with 10+ years of experience building production data layers for B2B SaaS platforms. You have deep expertise in SQLAlchemy 2.0 async ORM, Alembic migrations, PostgreSQL 15, and Pydantic v2 schema design.

---

#### TASK & OBJECTIVE

Implement all six SQLAlchemy database models for the AI Sales Outreach Automation project, create matching Pydantic Read/Create schemas, generate the initial Alembic migration, and deliver 3 passing async integration tests that confirm schema correctness and FK cascade behavior.

---

#### MY SITUATION

Phase 0 is complete — `pyproject.toml` exists, the `/backend` directory is scaffolded, and Alembic is initialized with an `alembic.ini` pointing at `DATABASE_URL`. PostgreSQL 15 is running in Docker on port 5432. The project uses `async` SQLAlchemy everywhere — no sync sessions.

---

#### CONSTRAINTS

- **All IDs are UUIDs** — `server_default=text("gen_random_uuid()")`. No auto-increment integers.
- **All timestamps are timezone-aware** — `DateTime(timezone=True)` everywhere.
- **No business logic in models** — pure ORM column definitions only.
- **Do not edit the generated Alembic migration file** once it runs. If it looks wrong, fix the model and regenerate.
- **Do not skip any table or column** — downstream phases reference all of them.
- Must match the exact table/column specs below — names, types, nullability, defaults, indexes.

---

#### AUDIENCE FOR THE OUTPUT

This schema is the single source of truth consumed by: FastAPI route handlers (Phase 2), LangGraph agents (Phase 3), and n8n webhook callbacks (Phase 4). Every column must be present and correctly typed or downstream phases will break.

---

#### PRIOR ATTEMPTS / WHAT FAILED

This is the first implementation. Avoid these common mistakes:
- Using `default=` instead of `server_default=` for DB-generated UUIDs and timestamps.
- Naive `DateTime` columns (missing `timezone=True`).
- Putting validation or computed properties on ORM models.
- Forgetting to import all models in `__init__.py` before running `alembic revision --autogenerate`.

---

#### FORMAT

Deliver one complete file at a time in this order:

1. `/backend/models/base.py`
2. `/backend/models/campaign.py`
3. `/backend/models/lead.py`
4. `/backend/models/email.py`
5. `/backend/models/reply.py`
6. `/backend/models/crm_update.py`
7. `/backend/models/oauth_token.py`
8. `/backend/models/__init__.py`
9. `/backend/schemas/` (one file per model)
10. Shell commands: `alembic revision --autogenerate` then `alembic upgrade head`
11. `/backend/tests/test_models.py`
12. Final verify block with exact expected output.

---

#### TONE & EXPERTISE LEVEL

Technical and precise. Assume expert-level SQLAlchemy and Python knowledge. No tutorial-style explanations. Do not add comments unless the line would genuinely surprise a senior engineer.

---

#### THINKING INSTRUCTION

Before writing any model, verify each column type against the spec below. Flag any SQLAlchemy 2.0 async gotchas (e.g. `server_default` vs `default`, relationship lazy-loading restrictions in async sessions) before writing code. If a spec is ambiguous, state the assumption and proceed.

---

#### DETAILED SPEC

**`/backend/models/base.py`**
```python
from sqlalchemy.orm import DeclarativeBase
class Base(DeclarativeBase): pass
```

**`/backend/models/campaign.py`** — table: `campaigns`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | `server_default=text("gen_random_uuid()")` |
| name | String(255) | not null |
| status | Enum("draft","active","paused","completed") | not null, default="draft" |
| settings | JSON | stores: target_audience, product, value_prop, case_study, tone |
| created_at | DateTime(timezone=True) | server_default=func.now() |
| updated_at | DateTime(timezone=True) | onupdate=func.now() |

**`/backend/models/lead.py`** — table: `leads`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| campaign_id | UUID FK → campaigns.id | ON DELETE CASCADE |
| company_name | String(255) | not null |
| website | String(500) | nullable |
| contact_name | String(255) | nullable |
| email | String(255) | not null |
| status | Enum("new","researched","email_sent","replied","meeting_booked","unsubscribed") | default="new" |
| research_data | JSON | nullable |
| created_at | DateTime(timezone=True) | server_default=func.now() |

Indexes: `idx_leads_email` on `email`, `idx_leads_campaign` on `campaign_id`

**`/backend/models/email.py`** — table: `emails`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| lead_id | UUID FK → leads.id | ON DELETE CASCADE |
| subject | Text | |
| body | Text | |
| type | Enum("outreach","followup") | not null |
| sent_at | DateTime(timezone=True) | nullable |
| opened_at | DateTime(timezone=True) | nullable |
| replied_at | DateTime(timezone=True) | nullable |
| gmail_message_id | String(255) | nullable |

Index: `idx_emails_lead` on `lead_id`

**`/backend/models/reply.py`** — table: `replies`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| email_id | UUID FK → emails.id | |
| content | Text | |
| classified_as | Enum("interested","not_interested","meeting_request","unsubscribe","needs_more_info","unknown") | default="unknown" |
| received_at | DateTime(timezone=True) | server_default=func.now() |

**`/backend/models/crm_update.py`** — table: `crm_updates`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| lead_id | UUID FK → leads.id | |
| platform | Enum("hubspot","airtable","notion") | |
| payload | JSON | |
| synced_at | DateTime(timezone=True) | server_default=func.now() |

**`/backend/models/oauth_token.py`** — table: `oauth_tokens`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID | nullable (single-user MVP) |
| provider | Enum("gmail","hubspot","slack") | not null |
| access_token_enc | LargeBinary | not null — will be Fernet-encrypted |
| refresh_token_enc | LargeBinary | nullable |
| expires_at | DateTime(timezone=True) | nullable |
| created_at | DateTime(timezone=True) | server_default=func.now() |

**Pydantic schemas** — `/backend/schemas/<model>.py` for each model:
- `<Model>Create` — no id, no timestamps, all required fields.
- `<Model>Read` — all fields, `model_config = ConfigDict(from_attributes=True)`.

**Tests** — `/backend/tests/test_models.py` using `pytest-asyncio` + async DB session from `conftest.py`:
- `test_create_campaign`: insert Campaign, flush, assert id is not None.
- `test_create_lead_with_fk`: insert Campaign + Lead, assert `campaign_id` FK resolves.
- `test_lead_email_cascade`: insert Campaign → Lead → Email; delete Lead; assert Email is gone.

**Verify:**
```bash
alembic upgrade head
# Expected: "Running upgrade  -> <rev>, initial_schema"

pytest backend/tests/test_models.py -v
# Expected: 3 passed
```

---

## Phase 1B — Qdrant Vector Store

| | |
|---|---|
| **Model** | `claude-sonnet-4-6` |
| **Skills** | `test-driven-development` |
| **Depends on** | Phase 1A complete (Alembic head applied) |

### Prompt

---

#### ROLE & PERSONA

You are a senior ML infrastructure engineer specializing in vector databases and embedding pipelines. You have production experience with Qdrant, the OpenAI embeddings API, and async Python service design.

---

#### TASK & OBJECTIVE

Build a `VectorStoreClient` singleton that manages two Qdrant collections (`company_research`, `email_templates`) with async upsert and semantic search methods, plus an `embed_text` helper, with all functionality covered by passing unit tests that mock external dependencies.

---

#### MY SITUATION

Phase 1A is complete — the Postgres schema and Alembic migration are applied. Qdrant is running in Docker on port 6333. The `qdrant-client` async library and `openai` SDK are already in `pyproject.toml`. `OPENAI_API_KEY` and `QDRANT_URL` are available via the settings module at `/backend/core/config.py`.

---

#### CONSTRAINTS

- `VectorStoreClient` must be a **singleton** — expose a `get_vector_store()` factory in `backend/core/__init__.py`.
- Do **not** call OpenAI directly inside `VectorStoreClient` — always import from `embeddings.py`.
- Do **not** add Qdrant collections beyond the two specified (`company_research`, `email_templates`).
- Both collections use `vector_size=1536` (text-embedding-3-small) and `distance=Cosine`.
- All methods are `async`.

---

#### AUDIENCE FOR THE OUTPUT

`VectorStoreClient` will be called by LangGraph agents (Phase 3) to store research summaries and retrieve best-fit email templates. The interface must be stable — method signatures are the contract.

---

#### PRIOR ATTEMPTS / WHAT FAILED

Do not use the synchronous `qdrant-client` API — the backend is fully async. Do not embed text inline inside `VectorStoreClient` methods — route through `embed_text()`. Do not create collections on every call — use `ensure_collections()` with an idempotent check.

---

#### FORMAT

Deliver files in this order:
1. `/backend/core/embeddings.py` — `embed_text` async function
2. `/backend/tests/test_embeddings.py` — mock OpenAI endpoint with `respx`
3. `/backend/core/vector_store.py` — `VectorStoreClient` class
4. `/backend/core/__init__.py` — `get_vector_store()` singleton factory
5. `/backend/tests/test_vector_store.py` — two tests with mocked qdrant-client + embeddings
6. Verify command + expected output.

---

#### TONE & EXPERTISE LEVEL

Expert-level. No boilerplate explanations. Async Python patterns assumed known.

---

#### THINKING INSTRUCTION

Before writing `VectorStoreClient`, think through the singleton pattern in an async context (thread safety, event loop lifecycle). Flag any gotchas with qdrant-client's async API initialization before writing code.

---

#### DETAILED SPEC

**`/backend/core/embeddings.py`**
```python
async def embed_text(text: str) -> list[float]:
    # Uses OpenAI text-embedding-3-small (1536 dims)
    # Reads OPENAI_API_KEY from settings
```

**`/backend/core/vector_store.py`** — `VectorStoreClient`:

Collections created by `ensure_collections()` (idempotent):
- `company_research`: payload fields — `company_name`, `website`, `lead_id` (str), `research_summary`, `timestamp` (ISO)
- `email_templates`: payload fields — `industry`, `pain_point`, `email_body`, `reply_rate` (float)

Methods:
```python
async def upsert_company_research(self, lead_id: str, summary_text: str, metadata: dict) -> None
    # embeds summary_text, upserts with point_id = lead_id (deterministic)

async def search_similar_companies(self, query_text: str, limit: int = 5) -> list[dict]
    # embeds query_text, searches company_research, returns payload dicts

async def upsert_email_template(self, template_data: dict) -> None
    # embeds template_data["email_body"], upserts to email_templates

async def get_best_templates(self, industry: str, pain_point: str, limit: int = 3) -> list[dict]
    # embeds f"{industry} {pain_point}", searches email_templates, returns payload dicts
```

**Tests** — mock both qdrant-client and `embed_text`:
- `test_upsert_and_search_company`: upsert one entry, search for it, assert payload returned.
- `test_get_best_templates`: upsert two templates, retrieve with query, assert top match first.

**Verify:**
```bash
pytest backend/tests/test_vector_store.py backend/tests/test_embeddings.py -v
# Expected: All tests pass
```

---

## Phase 2A — FastAPI Routes

| | |
|---|---|
| **Model** | `claude-sonnet-4-6` |
| **Skills** | `test-driven-development` (invoke before writing any route code) |
| **Depends on** | Phase 1A + 1B complete |

### Prompt

---

#### ROLE & PERSONA

You are a senior FastAPI engineer with extensive experience building production REST APIs for B2B SaaS platforms. You write clean async route handlers, understand N+1 query elimination, and design stable webhook contracts.

---

#### TASK & OBJECTIVE

Implement all FastAPI routers (campaigns, leads, emails, webhooks, auth, internal) with the standard `{ "data", "error", "meta" }` response envelope, CORS and logging middleware, CSV bulk-import for leads, and full test coverage using `httpx.AsyncClient` — achieving zero test failures.

---

#### MY SITUATION

Phases 1A and 1B are complete — all Postgres models, Pydantic schemas, and the Qdrant vector client are built. The FastAPI app exists at `/backend/main.py` with a `/health` route. The backend runs on port 8000. `N8N_WEBHOOK_URL` and `INTERNAL_API_TOKEN` are available from settings.

---

#### CONSTRAINTS

- **No direct external service calls from routes** — all LLM, Gmail, and Qdrant calls go through `services/` or `agents_interface/`.
- **No 500s for business logic errors** — use the `err()` helper with a specific error code string.
- **No `print()`** — `logging` module only.
- **No skipping tests** — every router needs a test file.
- Stats queries on campaigns must use a **single DB query** (subquery or window function) — no N+1.
- CORS: allow only `http://localhost:3000`.
- n8n webhook call on campaign activation is **fire-and-forget** — network failure must not fail the request.

---

#### AUDIENCE FOR THE OUTPUT

These routes are consumed by: the Next.js frontend (Phase 5), n8n automation workflows (Phase 4), and internal agent triggers (Phase 3). Response shape stability is critical — any deviation breaks all consumers.

---

#### PRIOR ATTEMPTS / WHAT FAILED

Do not use `response_model=` on routes that return the custom envelope — it will strip fields. Return `JSONResponse` or plain dicts with the envelope shape instead. Do not use `db.execute(select(...))` patterns that trigger lazy-loading in async sessions — use `selectinload` or explicit joins.

---

#### FORMAT

Deliver files in this order:
1. `/backend/core/response.py` — `ok()`, `paginated()`, `err()` helpers
2. `/backend/main.py` additions — CORS + logging middleware
3. `/backend/api/campaigns.py` — 4 routes
4. `/backend/api/leads.py` — 3 routes
5. `/backend/api/emails.py` — 2 routes
6. `/backend/api/webhooks.py` — 2 routes
7. `/backend/api/auth.py` — 3 routes
8. `/backend/api/internal.py` — 4 routes
9. Test files for each router
10. Verify commands + expected output.

---

#### TONE & EXPERTISE LEVEL

Expert. No explanatory scaffolding. FastAPI, SQLAlchemy async, and httpx.AsyncClient patterns assumed known.

---

#### THINKING INSTRUCTION

Before writing the campaigns list route, think through the stats subquery design to avoid N+1. Before writing the CSV upload route, think through bulk-insert semantics in SQLAlchemy async. Flag any async session scoping issues (e.g. background tasks) before writing code.

---

#### DETAILED SPEC

**`/backend/core/response.py`**
```python
def ok(data, meta=None) → {"data": data, "error": None, "meta": meta or {}}
def paginated(data, page, size, total) → ok(data, {"page": page, "size": size, "total": total})
def err(code, message, status=400) → raise HTTPException(status_code=status,
    detail={"data": None, "error": {"code": code, "message": message}, "meta": {}})
```

**`/backend/api/campaigns.py`**
- `POST /api/campaigns` — body: CampaignCreate → 201, CampaignRead
- `GET /api/campaigns?page=1&size=20` — paginated CampaignRead list, each with stats: `{ leads_count, emails_sent, open_rate, reply_rate, meetings_booked }`
- `GET /api/campaigns/{id}` — CampaignRead + stats dict
- `PATCH /api/campaigns/{id}/status` — body: `{ "status": "active"|"paused"|"completed" }` → updated CampaignRead. On `"active"`: async POST to `N8N_WEBHOOK_URL/campaign-launcher` with `{ "campaign_id": id }` (fire-and-forget, log errors, never fail request).

**`/backend/api/leads.py`**
- `POST /api/leads/upload` — multipart: `file` (CSV), `campaign_id` (UUID). Required columns: `company_name`, `email`. Optional: `website`, `contact_name`. Skip rows with invalid email (RFC-5322 basic regex). Bulk-insert via `session.execute(insert(Lead), [...])`. Return: `{ "inserted": N, "skipped": M, "errors": [{"row": 3, "reason": "invalid email"}] }`
- `GET /api/leads?campaign_id=&status=&page=&size=` — paginated LeadRead
- `GET /api/leads/{id}` — LeadRead + list of EmailRead (each with list of ReplyRead)

**`/backend/api/emails.py`**
- `GET /api/emails?lead_id=` — list of EmailRead, ordered by `sent_at` desc
- `POST /api/emails/{id}/resend` — look up email + lead, POST to internal trigger-personalization endpoint, return `{ "queued": true }`

**`/backend/api/webhooks.py`**
- `POST /api/webhooks/n8n/reply-received` — body: `{ gmail_message_id, reply_text, received_at }`. Steps: (1) find Email by `gmail_message_id` → 404 if missing; (2) insert Reply with `classified_as="unknown"`; (3) call reply-classifier agent stub, catch `NotImplementedError`, leave `classified_as="unknown"`; (4) update `Lead.status="replied"` and `Email.replied_at=now()`; (5) return `{ "reply_id": uuid, "classified_as": "unknown" }`.
- `POST /api/webhooks/n8n/email-opened` — body: `{ email_id, opened_at }`. Update `Email.opened_at`. Return 200.

**`/backend/api/auth.py`**
- `GET /api/auth/gmail` → `{ "auth_url": "<placeholder>" }`
- `GET /api/auth/gmail/callback` → 501 Not Implemented
- (Phase 2B will replace these)

**`/backend/api/internal.py`** — all routes require header `X-Internal-Token` matching `INTERNAL_API_TOKEN`; return 401 if missing or wrong.
- `POST /api/internal/trigger-research` — body: `{ lead_id }` → `{ "queued": true, "lead_id": lead_id }`
- `POST /api/internal/trigger-personalization` — same pattern
- `GET /api/internal/leads-needing-followup` — leads where `status="email_sent"`, no Reply exists, latest `Email.sent_at` is 3, 7, or 14 days ago (±12h). Returns: `[{ lead_id, days_since_sent }]`
- `POST /api/internal/trigger-followup` — body: `{ lead_id }` → `{ "queued": true }`

**Minimum test coverage:**
- `test_campaigns.py`: create, list, get, patch status
- `test_leads.py`: upload valid CSV, upload CSV with 1 bad row, list, get detail
- `test_webhooks.py`: reply-received happy path; reply-received unknown `gmail_message_id` → 404
- `test_internal.py`: missing token → 401, valid token → 200

**Verify:**
```bash
pytest backend/tests/ -v
# Expected: All tests pass. Zero failures.

uvicorn main:app --reload --port 8000 &
curl http://localhost:8000/health
# Expected: { "status": "ok" }
```

---

## Phase 2B — Gmail OAuth

| | |
|---|---|
| **Model** | `claude-sonnet-4-6` |
| **Skills** | `test-driven-development` |
| **Depends on** | Phase 2A complete |

### Prompt

---

#### ROLE & PERSONA

You are a senior backend security engineer with deep experience in OAuth2 flows, token encryption, and Gmail API integration. You have built compliant, production-hardened email-sending services with quota management.

---

#### TASK & OBJECTIVE

Implement encrypted Gmail OAuth2 token storage, a `GmailService` class that sends emails within a 100/day Redis rate limit, wire up the auth router callbacks, and deliver 5 passing unit tests that mock all external APIs.

---

#### MY SITUATION

Phase 2A is complete. The `oauth_tokens` table exists in Postgres (Phase 1A). Redis is running in Docker. The `google-api-python-client` and `cryptography` libraries are in `pyproject.toml`. `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `FERNET_KEY`, `BACKEND_URL`, and `FRONTEND_URL` are read from settings. This is a single-user MVP — no multi-user token separation yet.

---

#### CONSTRAINTS

- **Do not use `smtplib`** or any third-party email wrapper — use only the Google API Python client (`google-api-python-client`).
- **Tokens must be encrypted at rest** — Fernet-encrypt before persisting, decrypt only inside `_get_credentials()`.
- **Do not bypass the Redis rate limit** — 100 emails/Gmail account/day is a hard quota, not a stub.
- **`FERNET_KEY` must be added to `.env.example`** with a generation command comment.
- No plaintext secrets in any file.

---

#### AUDIENCE FOR THE OUTPUT

`GmailService` is called by n8n webhook handlers (Phase 4) and the internal resend route. `_get_credentials()` is called on every send — it must handle token refresh transparently without leaking plaintext to logs.

---

#### PRIOR ATTEMPTS / WHAT FAILED

Do not use `google-auth-oauthlib` Flow's synchronous `run_local_server()` — build the auth URL manually. Do not store the raw access token string in any variable that could appear in a log statement. Do not call `redis.incr()` after a failed Gmail send — increment only on confirmed success.

---

#### FORMAT

Deliver files in this order:
1. `/backend/core/crypto.py` — `encrypt_bytes()` / `decrypt_bytes()`
2. `.env.example` addition — `FERNET_KEY` entry with generation comment
3. `/backend/services/gmail_service.py` — `GmailService` class (all 5 methods)
4. `/backend/core/exceptions.py` — `GmailQuotaExceededError`, `GmailNotConnectedError` + FastAPI exception handlers
5. `/backend/api/auth.py` — replace placeholder with real `GmailService` calls
6. `/backend/tests/test_gmail_service.py` — 5 tests using `respx`
7. Verify commands + expected output.

---

#### TONE & EXPERTISE LEVEL

Expert. Assume deep knowledge of OAuth2, Fernet encryption, and async Python. No tutorial-level comments.

---

#### THINKING INSTRUCTION

Before writing `_get_credentials()`, think through the token refresh race condition in a concurrent async context and decide whether a DB-level lock or application-level lock is needed for this MVP. State your decision and rationale before writing the method.

---

#### DETAILED SPEC

**`/backend/core/crypto.py`**
```python
def encrypt_bytes(plaintext: bytes) -> bytes  # reads FERNET_KEY from settings
def decrypt_bytes(ciphertext: bytes) -> bytes
```

**`/backend/services/gmail_service.py`** — `GmailService`:
```python
SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]

async def get_auth_url(self) -> str
    # Build OAuth2 URL. redirect_uri = "{BACKEND_URL}/api/auth/gmail/callback"

async def exchange_code(self, code: str, db: AsyncSession) -> None
    # Exchange code for tokens, encrypt both, upsert into oauth_tokens (provider="gmail")

async def _get_credentials(self, db: AsyncSession)
    # Load token, decrypt, build Credentials. If expired: refresh, re-encrypt, save back to DB.

async def send_email(self, to: str, subject: str, body: str, reply_to: str | None, db: AsyncSession) -> str
    # Check Redis key "gmail:sent:{date}" — if >= 100, raise GmailQuotaExceededError
    # Build MIME message, call Gmail API messages().send()
    # Increment Redis counter (TTL = end of day)
    # Return message_id

async def create_draft(self, to: str, subject: str, body: str, db: AsyncSession) -> str
    # Create Gmail draft, return draft_id

async def list_recent_replies(self, since_timestamp: datetime, db: AsyncSession) -> list[dict]
    # Search Gmail: "is:inbox after:{timestamp}"
    # Return [{ gmail_message_id, from, subject, snippet, received_at }]
```

**`/backend/core/exceptions.py`**
```python
class GmailQuotaExceededError(Exception): pass
class GmailNotConnectedError(Exception): pass
# Register as FastAPI exception handlers returning standard error envelope shape
```

**`/backend/api/auth.py`** — replace stubs:
- `GET /api/auth/gmail` → `{ "data": { "auth_url": await gmail_service.get_auth_url() } }`
- `GET /api/auth/gmail/callback?code=...` → call `exchange_code(code, db)`, redirect to `{FRONTEND_URL}/settings?gmail=connected`
- `GET /api/auth/gmail/status` → `{ "data": { "connected": bool, "email": str | null } }` — check if `oauth_tokens` row exists for `provider="gmail"`

**Tests** — 5 tests using `respx` to mock Google OAuth and Gmail API:
- `test_get_auth_url`: assert URL contains correct `client_id` and scopes
- `test_exchange_code`: mock token endpoint, assert token saved encrypted in DB
- `test_send_email_success`: mock Gmail API, assert `message_id` returned, Redis counter incremented
- `test_send_email_quota_exceeded`: pre-set Redis counter to 100, assert `GmailQuotaExceededError`
- `test_token_refresh`: mock refresh endpoint, assert new token saved back to DB

**Verify:**
```bash
pytest backend/tests/test_gmail_service.py -v
# Expected: 5 passed

# Then manually walk the OAuth flow:
# 1. GET /api/auth/gmail → copy auth_url
# 2. Open in browser → authorize with a test Google account
# 3. GET /api/auth/gmail/status → { "connected": true }
```

---

## After Phase 2

1. `pytest backend/tests/ -v` — all tests green.
2. Update `CLAUDE.md`: Phase 1 and Phase 2 → ✅ complete.
3. Note any Google API quirks or rate-limit edge cases in `scratchpad.md`.
4. Commit. Open Phase 3 (Agents) in a new session.
