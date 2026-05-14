# 02 — Database Schema

Two stores: **PostgreSQL** (relational source of truth) + **Qdrant** (semantic memory).
Redis is also used but only for ephemeral counters/rate-limits — no schema there.

## PostgreSQL (`postgres:15`)

All tables use UUID PKs (server-generated, `gen_random_uuid()`), UTC timestamps.

### `campaigns`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| name | TEXT NOT NULL | |
| status | ENUM | `draft / active / paused / completed` |
| settings | JSONB | tone, target audience, product, value prop, case study |
| created_at | TIMESTAMPTZ | default `now()` |

### `leads`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| campaign_id | UUID FK → campaigns.id | ON DELETE CASCADE |
| company_name | TEXT NOT NULL | |
| website | TEXT | |
| contact_name | TEXT | |
| email | TEXT NOT NULL | indexed |
| status | ENUM | `new / researched / email_sent / replied / meeting_booked / unsubscribed` |
| research_data | JSONB | output of Research Agent |
| created_at | TIMESTAMPTZ | |

**Indexes:** `idx_leads_email (email)`, `idx_leads_campaign (campaign_id)`.

### `emails`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| lead_id | UUID FK → leads.id | indexed |
| subject | TEXT | |
| body | TEXT | |
| type | ENUM | `outreach / followup` |
| sent_at | TIMESTAMPTZ | nullable until sent |
| opened_at | TIMESTAMPTZ | from tracking pixel |
| replied_at | TIMESTAMPTZ | mirrored from `replies` |
| gmail_message_id | TEXT | for threading |

### `replies`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| email_id | UUID FK → emails.id | |
| content | TEXT | |
| classified_as | ENUM | `interested / not_interested / meeting_request / unsubscribe / unknown` |
| received_at | TIMESTAMPTZ | |

### `crm_updates`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| lead_id | UUID FK → leads.id | |
| platform | ENUM | `hubspot / airtable / notion` |
| payload | JSONB | exact body sent |
| synced_at | TIMESTAMPTZ | |

### `oauth_tokens`
| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | UUID | future multi-user support |
| provider | ENUM | `gmail / hubspot / slack` |
| access_token_enc | BYTEA | Fernet-encrypted |
| refresh_token_enc | BYTEA | |
| expires_at | TIMESTAMPTZ | |

## Migrations
- Tooling: **Alembic** with autogenerate.
- Convention: `alembic revision --autogenerate -m "<verb_subject>"`.
- **Never edit a generated migration file** once committed. Add a new revision instead.

## Qdrant Collections

Vector size 1536 (OpenAI `text-embedding-3-small`). Distance: `Cosine`.

### `company_research`
| Payload field | Type |
|---------------|------|
| company_name | string |
| website | string |
| lead_id | uuid (string) |
| research_summary | string (2–3 sentences) |
| timestamp | ISO-8601 string |

### `email_templates`
| Payload field | Type |
|---------------|------|
| industry | string |
| pain_point | string |
| email_body | string |
| reply_rate | float (0–1) |

## Client
`/backend/core/vector_store.py` exposes a single `VectorStoreClient` (async, `qdrant-client`). Methods:
- `upsert_company_research(lead_id, summary_text, metadata)`
- `search_similar_companies(query_text, limit=5) -> List[dict]`
- `upsert_email_template(template_data)`
- `get_best_templates(industry, pain_point) -> List[dict]`

Embedding generation lives in `/backend/core/embeddings.py` so the vector store stays storage-only.
