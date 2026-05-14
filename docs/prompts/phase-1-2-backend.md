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

```
Read CLAUDE.md before starting.

## Context
Phase 1A of the AI Sales Outreach Automation project. We are building the PostgreSQL schema
using SQLAlchemy 2.0 async ORM + Alembic. Phase 0 is complete — pyproject.toml exists,
the backend structure exists, Alembic is initialized.

## Task
Implement all database models and generate the initial migration.

### Step 1 — SQLAlchemy models in /backend/models/

Create /backend/models/base.py:
  from sqlalchemy.orm import DeclarativeBase
  class Base(DeclarativeBase): pass

Create /backend/models/campaign.py:
  Table: campaigns
  Columns:
    id: UUID, primary key, server_default=text("gen_random_uuid()")
    name: String(255), not null
    status: Enum("draft","active","paused","completed"), not null, default="draft"
    settings: JSON (stores: target_audience, product, value_prop, case_study, tone)
    created_at: DateTime(timezone=True), server_default=func.now()
    updated_at: DateTime(timezone=True), onupdate=func.now()

Create /backend/models/lead.py:
  Table: leads
  Columns:
    id: UUID PK
    campaign_id: UUID FK → campaigns.id, ON DELETE CASCADE
    company_name: String(255), not null
    website: String(500)
    contact_name: String(255)
    email: String(255), not null
    status: Enum("new","researched","email_sent","replied","meeting_booked","unsubscribed"), default="new"
    research_data: JSON (nullable)
    created_at: DateTime(timezone=True), server_default=func.now()
  Indexes: Index("idx_leads_email", "email"), Index("idx_leads_campaign", "campaign_id")

Create /backend/models/email.py:
  Table: emails
  Columns:
    id: UUID PK
    lead_id: UUID FK → leads.id, ON DELETE CASCADE
    subject: Text
    body: Text
    type: Enum("outreach","followup"), not null
    sent_at: DateTime(timezone=True), nullable
    opened_at: DateTime(timezone=True), nullable
    replied_at: DateTime(timezone=True), nullable
    gmail_message_id: String(255), nullable
  Indexes: Index("idx_emails_lead", "lead_id")

Create /backend/models/reply.py:
  Table: replies
  Columns:
    id: UUID PK
    email_id: UUID FK → emails.id
    content: Text
    classified_as: Enum("interested","not_interested","meeting_request","unsubscribe","needs_more_info","unknown"), default="unknown"
    received_at: DateTime(timezone=True), server_default=func.now()

Create /backend/models/crm_update.py:
  Table: crm_updates
  Columns:
    id: UUID PK
    lead_id: UUID FK → leads.id
    platform: Enum("hubspot","airtable","notion")
    payload: JSON
    synced_at: DateTime(timezone=True), server_default=func.now()

Create /backend/models/oauth_token.py:
  Table: oauth_tokens
  Columns:
    id: UUID PK
    user_id: UUID (nullable for now — single-user MVP)
    provider: Enum("gmail","hubspot","slack"), not null
    access_token_enc: LargeBinary, not null  (will be Fernet-encrypted)
    refresh_token_enc: LargeBinary, nullable
    expires_at: DateTime(timezone=True), nullable
    created_at: DateTime(timezone=True), server_default=func.now()

Create /backend/models/__init__.py that imports all models so Alembic can detect them.

### Step 2 — Pydantic schemas in /backend/schemas/

Create a /backend/schemas/ directory (parallel to /models/).
For each model, create a Read schema (UUID id, all fields) and a Create schema (no id, no timestamps).
Example pattern:
  class CampaignCreate(BaseModel):
      name: str
      settings: dict = {}

  class CampaignRead(CampaignCreate):
      id: UUID
      status: str
      created_at: datetime
      model_config = ConfigDict(from_attributes=True)

### Step 3 — Alembic migration
Run: cd backend && alembic revision --autogenerate -m "initial_schema"
Then: alembic upgrade head

Do NOT edit the generated migration file. If it doesn't look right, fix the models and regenerate.

### Step 4 — Test
Write /backend/tests/test_models.py:
  - test_create_campaign: insert a Campaign, flush, assert id is not None
  - test_create_lead_with_fk: insert a Campaign + a Lead, assert campaign_id FK resolves
  - test_lead_email_cascade: insert Campaign, Lead, Email; delete Lead; assert Email is gone

Use pytest-asyncio with the async DB session from conftest.py.

## Constraints
- Do NOT skip any column or table — they will be referenced in later phases.
- Do NOT modify alembic.ini or the generated migration file once it runs.
- All IDs are UUIDs. No auto-increment integers.
- All timestamps are timezone-aware (DateTime(timezone=True)).
- Do NOT add any business logic to models — they are pure ORM definitions.

## Verify
Run: alembic upgrade head
Expected: "Running upgrade  -> <rev>, initial_schema"

Run: pytest backend/tests/test_models.py -v
Expected: 3 tests pass.
```

---

## Phase 1B — Qdrant Vector Store

| | |
|---|---|
| **Model** | `claude-sonnet-4-6` |
| **Skills** | `test-driven-development` |
| **Depends on** | Phase 1A complete (Alembic head applied) |

### Prompt

```
Read CLAUDE.md before starting.

## Context
Phase 1B: Qdrant vector store client. Qdrant is running in Docker on port 6333.
The async qdrant-client is already in pyproject.toml (installed in Phase 0).
We need a single VectorStoreClient class that the backend (and later the agents) use.

## Task

### Step 1 — Embeddings helper: /backend/core/embeddings.py
Create an async function:
  async def embed_text(text: str) -> list[float]:
      Uses OpenAI text-embedding-3-small (1536 dims).
      Reads OPENAI_API_KEY from settings.
      Returns a list of floats.

Write test: /backend/tests/test_embeddings.py
  Use respx to mock the OpenAI embeddings endpoint.
  Assert the return is a list of 1536 floats.

### Step 2 — VectorStoreClient: /backend/core/vector_store.py

class VectorStoreClient:
    Initialized with qdrant_url from settings.
    On first use, calls ensure_collections() which creates collections if they don't exist.

    Collections:
      company_research:
        vector_size=1536, distance=Cosine
        payload fields: company_name, website, lead_id (str), research_summary, timestamp (ISO)
      email_templates:
        vector_size=1536, distance=Cosine
        payload fields: industry, pain_point, email_body, reply_rate (float)

    Methods (all async):

    async def upsert_company_research(
        self,
        lead_id: str,
        summary_text: str,
        metadata: dict,
    ) -> None:
        Embeds summary_text, upserts with point_id = lead_id (deterministic).

    async def search_similar_companies(
        self,
        query_text: str,
        limit: int = 5,
    ) -> list[dict]:
        Embeds query_text, searches company_research, returns payload dicts.

    async def upsert_email_template(self, template_data: dict) -> None:
        Embeds template_data["email_body"], upserts to email_templates.

    async def get_best_templates(
        self,
        industry: str,
        pain_point: str,
        limit: int = 3,
    ) -> list[dict]:
        Embeds f"{industry} {pain_point}", searches email_templates, returns payload dicts.

### Step 3 — Tests: /backend/tests/test_vector_store.py
  Mock both qdrant-client and the embeddings helper.
  test_upsert_and_search_company: upsert one entry, search for it, assert payload returned.
  test_get_best_templates: upsert two templates, retrieve with query, assert top match first.

## Constraints
- The VectorStoreClient must be a singleton: expose a get_vector_store() factory in core/__init__.py.
- Do NOT call OpenAI directly inside VectorStoreClient — always import from embeddings.py.
- Do NOT add any other Qdrant collections beyond the two specified.

## Verify
Run: pytest backend/tests/test_vector_store.py backend/tests/test_embeddings.py -v
Expected: All tests pass.
```

---

## Phase 2A — FastAPI Routes

| | |
|---|---|
| **Model** | `claude-sonnet-4-6` |
| **Skills** | `test-driven-development` (invoke before writing any route code) |
| **Depends on** | Phase 1A + 1B complete |

### Prompt

```
Read CLAUDE.md before starting.

## Context
Phase 2A: implement all FastAPI routes. The models, schemas, and DB session are already built
in Phases 1A/1B. The backend runs on port 8000. All responses must follow:
  { "data": <payload>, "error": null, "meta": { "page": 1, "size": 20, "total": 100 } }

## Task

### Step 1 — Response helpers: /backend/core/response.py
Create three helpers:
  def ok(data, meta=None) → {"data": data, "error": None, "meta": meta or {}}
  def paginated(data, page, size, total) → ok(data, {"page": page, "size": size, "total": total})
  def err(code, message, status=400) → raise HTTPException(status_code=status, detail={"data": None, "error": {"code": code, "message": message}, "meta": {}})

### Step 2 — Middleware: /backend/main.py
Add to the existing main.py:
  - CORSMiddleware: allow origins ["http://localhost:3000"], all methods, all headers
  - Request/response logging middleware: log method, path, status code, duration (ms) using the logging module — NOT print.

### Step 3 — Campaigns router: /backend/api/campaigns.py
  POST /api/campaigns
    Body: CampaignCreate schema
    Returns: 201, CampaignRead

  GET /api/campaigns?page=1&size=20
    Returns: paginated list of CampaignRead
    Each item includes a stats sub-object:
      { leads_count: int, emails_sent: int, open_rate: float, reply_rate: float, meetings_booked: int }
    Compute stats with a single DB query (window functions or subquery — avoid N+1).

  GET /api/campaigns/{id}
    Returns: CampaignRead + same stats dict

  PATCH /api/campaigns/{id}/status
    Body: { "status": "active" | "paused" | "completed" }
    Returns: updated CampaignRead
    When moving to "active": make an async HTTP POST to N8N_WEBHOOK_URL/campaign-launcher
      with { "campaign_id": id }. If n8n is unreachable, log the error but still return 200
      (fire-and-forget — do not fail the request).

### Step 4 — Leads router: /backend/api/leads.py
  POST /api/leads/upload
    multipart/form-data: file (CSV), campaign_id (UUID)
    Parse CSV with Python csv module. Required columns: company_name, email.
    Optional: website, contact_name.
    Validate: skip rows with missing or invalid email (RFC-5322 basic check via regex).
    Bulk-insert with session.execute(insert(Lead), [...]).
    Return: { "data": { "inserted": N, "skipped": M, "errors": [{"row": 3, "reason": "invalid email"}] } }

  GET /api/leads?campaign_id=&status=&page=&size=
    Returns: paginated LeadRead list.

  GET /api/leads/{id}
    Returns: LeadRead + list of EmailRead (each with list of ReplyRead).

### Step 5 — Emails router: /backend/api/emails.py
  GET /api/emails?lead_id=
    Returns: list of EmailRead for that lead, ordered by sent_at desc.

  POST /api/emails/{id}/resend
    Look up the email and its lead. POST to internal trigger-personalization endpoint.
    Return: { "data": { "queued": true } }

### Step 6 — Webhooks router: /backend/api/webhooks.py
  POST /api/webhooks/n8n/reply-received
    Body: { gmail_message_id: str, reply_text: str, received_at: ISO datetime }
    Steps:
      1. Find the Email row by gmail_message_id. Return 404 if not found.
      2. Insert a Reply row with classified_as="unknown".
      3. Queue classification (for now: call /agents/reply_classifier stub inline,
         catch NotImplementedError, leave classified_as="unknown").
      4. Update Lead.status = "replied", Email.replied_at = now().
      5. Return: { "data": { "reply_id": uuid, "classified_as": "unknown" } }

  POST /api/webhooks/n8n/email-opened
    Body: { email_id: UUID, opened_at: ISO datetime }
    Update Email.opened_at. Return 200.

### Step 7 — Auth router: /backend/api/auth.py
  GET /api/auth/gmail
    Return: { "data": { "auth_url": "<placeholder - to be implemented Phase 2B>" } }

  GET /api/auth/gmail/callback
    Return 501 Not Implemented for now.

### Step 8 — Internal router: /backend/api/internal.py
Add to the FastAPI app with prefix /api/internal.
All internal routes check header X-Internal-Token matches INTERNAL_API_TOKEN from settings.
Return 401 if missing or wrong.

  POST /api/internal/trigger-research
    Body: { lead_id: UUID }
    Return: { "data": { "queued": true, "lead_id": lead_id } }
    (Calls agents_interface stub — NotImplementedError is caught and logged, returns queued: true)

  POST /api/internal/trigger-personalization
    Same pattern as trigger-research.

  GET /api/internal/leads-needing-followup
    Return leads where: status = "email_sent" AND no Reply exists AND
    latest Email.sent_at is 3, 7, or 14 days ago (within ±12 hours).
    Returns: list of { lead_id, days_since_sent }.

  POST /api/internal/trigger-followup
    Body: { lead_id: UUID }
    Returns: { "data": { "queued": true } }

### Step 9 — Tests
Write tests in /backend/tests/ for every router. Use httpx.AsyncClient.
At minimum:
  test_campaigns.py: create, list, get, patch status
  test_leads.py: upload valid CSV, upload CSV with 1 bad row, list, get detail
  test_webhooks.py: reply-received happy path, reply-received unknown gmail_message_id → 404
  test_internal.py: missing token → 401, valid token → 200

## Constraints
- Do NOT call any external service (LLM, Gmail, Qdrant) directly from routes.
  All external calls go through services/ or agents_interface/.
- Do NOT return 500 for business logic errors — use the err() helper with a specific error code.
- Do NOT use print() anywhere — logging module only.
- Do NOT skip writing tests for any router.

## Verify
Run: pytest backend/tests/ -v
Expected: All tests pass. Zero failures.

Run: cd backend && uvicorn main:app --reload --port 8000 &
Then: curl http://localhost:8000/health
Expected: { "status": "ok" }
```

---

## Phase 2B — Gmail OAuth

| | |
|---|---|
| **Model** | `claude-sonnet-4-6` |
| **Skills** | `test-driven-development` |
| **Depends on** | Phase 2A complete |

### Prompt

```
Read CLAUDE.md before starting.

## Context
Phase 2B: Gmail OAuth2 integration. This is the service that the n8n workflows use
to send emails and monitor replies. Tokens must be stored encrypted in the oauth_tokens
table created in Phase 1A. Rate limit: 100 emails per Gmail account per day via Redis.

## Task

### Step 1 — Token encryption helper: /backend/core/crypto.py
Using the Python cryptography library (Fernet):
  def encrypt_bytes(plaintext: bytes) -> bytes:
      Reads FERNET_KEY from settings (generate one if missing: Fernet.generate_key())
  def decrypt_bytes(ciphertext: bytes) -> bytes:

Add FERNET_KEY to .env.example (comment: generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

### Step 2 — GmailService: /backend/services/gmail_service.py
Use the raw Google API Python client (google-api-python-client) — NOT any third-party wrapper.

class GmailService:
    SCOPES = ["https://www.googleapis.com/auth/gmail.send",
              "https://www.googleapis.com/auth/gmail.readonly"]

    async def get_auth_url(self) -> str:
        Build and return the OAuth2 authorization URL.
        Reads GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET from settings.
        redirect_uri = "{BACKEND_URL}/api/auth/gmail/callback"

    async def exchange_code(self, code: str, db: AsyncSession) -> None:
        Exchange the authorization code for tokens.
        Encrypt access_token + refresh_token using crypto.py.
        Upsert into oauth_tokens (provider="gmail").

    async def _get_credentials(self, db: AsyncSession):
        Load the gmail token from oauth_tokens, decrypt, build google.oauth2.credentials.Credentials.
        If token is expired, refresh it, re-encrypt, and save back to DB.

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        reply_to: str | None = None,
        db: AsyncSession = None,
    ) -> str:  # returns gmail message ID
        Check Redis rate limit key "gmail:sent:{date}" — if >= 100, raise GmailQuotaExceededError.
        Build MIME message, call Gmail API messages().send().
        Increment Redis counter (TTL = end of day).
        Return message_id.

    async def create_draft(self, to: str, subject: str, body: str, db: AsyncSession) -> str:
        Create a Gmail draft. Returns draft_id.

    async def list_recent_replies(self, since_timestamp: datetime, db: AsyncSession) -> list[dict]:
        Search Gmail: "is:inbox after:{timestamp}".
        Return list of { gmail_message_id, from, subject, snippet, received_at }.

### Step 3 — Wire up auth router: /backend/api/auth.py
  GET /api/auth/gmail
    Return: { "data": { "auth_url": await gmail_service.get_auth_url() } }

  GET /api/auth/gmail/callback?code=...
    Call gmail_service.exchange_code(code, db).
    Redirect to: "{FRONTEND_URL}/settings?gmail=connected"

  GET /api/auth/gmail/status
    Return: { "data": { "connected": bool, "email": str | null } }
    Check if an oauth_token for gmail exists in DB.

### Step 4 — Error types: /backend/core/exceptions.py
  class GmailQuotaExceededError(Exception): pass
  class GmailNotConnectedError(Exception): pass
  Register these as FastAPI exception handlers returning the standard error shape.

### Step 5 — Tests: /backend/tests/test_gmail_service.py
Use respx to mock the Google OAuth token endpoint and Gmail API.
  test_get_auth_url: assert URL contains correct client_id and scopes
  test_exchange_code: mock token endpoint, assert token saved encrypted in DB
  test_send_email_success: mock Gmail API, assert message_id returned, Redis counter incremented
  test_send_email_quota_exceeded: pre-set Redis counter to 100, assert GmailQuotaExceededError
  test_token_refresh: mock refresh endpoint, assert new token saved back to DB

## Constraints
- Do NOT use smtplib or any email-sending library — use only the Google API Python client.
- Do NOT store plaintext tokens — encrypt before persisting, decrypt only in _get_credentials.
- Do NOT bypass the Redis rate limit — it is a real constraint, not a stub.
- FERNET_KEY must be added to .env.example.

## Verify
Run: pytest backend/tests/test_gmail_service.py -v
Expected: 5 tests pass.

Then manually walk the OAuth flow:
  1. GET /api/auth/gmail → copy auth_url
  2. Open in browser → authorize with a test Google account
  3. GET /api/auth/gmail/status → { "connected": true }
```

---

## After Phase 2
1. `pytest backend/tests/ -v` — all tests green.
2. Update CLAUDE.md: Phase 2 → ✅ complete.
3. Note in `scratchpad.md` any Google API quirks or rate-limit edge cases.
4. Commit. Open Phase 3 (Agents) in a new session.
