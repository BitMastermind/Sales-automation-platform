# 04 — FastAPI Reference

Base URL (dev): `http://localhost:8000`
All responses follow `{ "data": ..., "error": null, "meta": {...} }`.

## Auth
Phase-0/1 has no user auth; the backend trusts localhost. Production will add OAuth on the frontend → JWT on backend. Gmail OAuth is per-account, handled in its own router.

## Public API

### Campaigns

#### `POST /api/campaigns`
Create a campaign.
```json
{
  "name": "AI Automation for Logistics",
  "settings": {
    "target_audience": "B2B logistics startups",
    "product": "Sales automation platform",
    "value_prop": "...",
    "case_study": "...",
    "tone": "professional_friendly"
  }
}
```
Returns `201` with the created campaign.

#### `GET /api/campaigns?page=1&size=20`
List with pagination. `meta` carries `{ page, size, total }`.

#### `GET /api/campaigns/{id}`
Detail + stats: `leads_count, emails_sent, open_rate, reply_rate, meetings_booked`.

#### `PATCH /api/campaigns/{id}/status`
Body: `{ "status": "active" }`. Triggers the n8n `campaign_launcher` workflow when moving to `active`.

### Leads

#### `POST /api/leads/upload`
`multipart/form-data` with `file` (CSV) and `campaign_id`. Server parses, validates, bulk-inserts.
Returns `{ data: { inserted: N, skipped: M, errors: [...] } }`.

#### `GET /api/leads?campaign_id=&status=&page=&size=`
Filtered list.

#### `GET /api/leads/{id}`
Lead detail + email history + replies.

### Emails

#### `GET /api/emails?lead_id=`
History for a lead.

#### `POST /api/emails/{id}/resend`
Re-queues an email through n8n.

### Auth (Gmail OAuth)

#### `GET /api/auth/gmail`
Returns `{ data: { auth_url: "..." } }` for the frontend to redirect to.

#### `GET /api/auth/gmail/callback?code=...`
Google's redirect target. Exchanges code, stores encrypted tokens, redirects back to `/settings?gmail=connected`.

### Webhooks (called by n8n)

#### `POST /api/webhooks/n8n/reply-received`
```json
{
  "gmail_message_id": "abc123",
  "reply_text": "...",
  "received_at": "2026-05-14T10:23:00Z"
}
```
Persists the reply, runs the Reply Classifier, updates `leads.status`.

#### `POST /api/webhooks/n8n/email-opened`
```json
{ "email_id": "uuid", "opened_at": "..." }
```

## Internal API
These exist for n8n only; they live under `/api/internal/` and require a shared secret header (`X-Internal-Token`).

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/internal/trigger-research` | Run Research Agent for one lead |
| POST | `/api/internal/trigger-personalization` | Run Personalization Agent + persist email |
| GET | `/api/internal/leads-needing-followup` | Returns leads with no reply within follow-up windows |
| POST | `/api/internal/trigger-followup` | Run Follow-up Agent for one lead |

## Standards
- All endpoints return `{ data, error, meta }`. Errors include `error.code` and `error.message`.
- All requests/responses are JSON unless explicitly multipart.
- All endpoints are async (`async def`).
- Logging: structured JSON via the `logging` module — never `print`.
- CORS in dev: `http://localhost:3000` only.
- Rate limit: 100 emails/day per Gmail account, tracked in Redis (key: `gmail:sent:{account}:{yyyymmdd}`).

## Error Codes (canonical)
| `error.code` | HTTP | Meaning |
|-------------|------|---------|
| `validation_failed` | 422 | Bad request body |
| `not_found` | 404 | Resource missing |
| `unauthorized` | 401 | Missing/invalid token |
| `gmail_quota_exceeded` | 429 | Daily Gmail cap hit |
| `agent_output_invalid` | 422 | LangGraph agent failed schema |
| `upstream_error` | 502 | Tavily/Firecrawl/LLM down |
