# n8n Credentials Reference (Phase 4)

These workflows are exported **without embedded secrets**. You must create the following credentials in the n8n UI **with the exact names** below, then import the workflows.

## 1) Gmail OAuth2 (required)
- **Credential name:** `Gmail Account`
- **n8n path:** Settings → Credentials → New → **Gmail OAuth2**
- **Notes:** Used by `Gmail — Send Email`, `Gmail — Search Replies`, `Gmail — Get Full Message`, `Gmail — Send Follow-up`.

## 2) Slack API (required)
- **Credential name:** `Slack Account`
- **n8n path:** Settings → Credentials → New → **Slack API**
- **Required scopes:** `chat:write`
- **Notes:** Used for `#sales-errors` (HTTP error outputs) and `#sales-replies` (interest notifications).

## 3) Google Sheets OAuth2 (required)
- **Credential name:** `Google Sheets Account`
- **n8n path:** Settings → Credentials → New → **Google Sheets OAuth2**
- **Notes:** The workflows reference sheet IDs via env vars:
  - `REPLY_MONITOR_SHEET_ID` (used by `gmail_reply_monitor`)
  - `FOLLOWUP_DAILY_SHEET_ID` (used by `followup_scheduler`)

## 4) HTTP Header Auth (FastAPI internal) (required)
- **Credential name:** `FastAPI Internal`
- **n8n path:** Settings → Credentials → New → **HTTP Header Auth**
- **Header name:** `X-Internal-Token`
- **Header value:** set to your internal token (from `.env`)
- **Notes:** All `/api/internal/*` HTTP nodes use this credential, and additionally set an `Idempotency-Key` header per request.

