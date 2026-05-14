# 05 — n8n Workflows

n8n is the **automation pipeline** — never the brain. Every reasoning step is an HTTP call to FastAPI (which in turn invokes a LangGraph agent).

## Conventions
- Webhook URLs come from the `N8N_WEBHOOK_URL` env var, never hardcoded.
- All HTTP nodes hitting FastAPI must include the `X-Internal-Token` header.
- After editing a workflow in the n8n UI, **re-export the JSON** and commit it.
- Workflows export to `/n8n-workflows/<name>.json`.

## Importing
1. `make dev` boots n8n at `http://localhost:5678`.
2. n8n UI → Workflows → Import from file → pick a JSON.
3. Set the credentials inside n8n (Gmail OAuth, Slack token, FastAPI internal base URL).
4. Activate.

---

## 1. `campaign_launcher.json`

### Trigger
Webhook (POST). Called by FastAPI when a campaign transitions to `active`.

### Payload
```json
{ "campaign_id": "uuid" }
```

### Nodes
1. **HTTP: Fetch leads** — `GET /api/internal/leads?campaign_id={{ $json.campaign_id }}&status=new`
2. **Split In Batches** — batch size 1.
3. **HTTP: Trigger research** — `POST /api/internal/trigger-research`, body `{ "lead_id": ... }`
4. **HTTP: Trigger personalization** — `POST /api/internal/trigger-personalization`, body `{ "lead_id": ... }`
5. **Gmail: Send** — uses email returned by step 4.
6. **HTTP: Mark sent** — `PATCH /api/internal/leads/{id}` body `{ "status": "email_sent", "gmail_message_id": ... }`.
7. **Wait** — 30 seconds (rate-limit between leads).

### Failure handling
On any non-2xx response: branch to a `Slack: notify` node with the error payload, then continue to the next lead.

---

## 2. `gmail_reply_monitor.json`

### Trigger
Schedule — every 15 minutes.

### Nodes
1. **HTTP: Get watched message IDs** — `GET /api/internal/sent-emails/recent` (last 14 days).
2. **Gmail: Search** — `is:inbox` + threading on those IDs.
3. **For each new reply:**
   - **HTTP: POST reply** — `POST /api/webhooks/n8n/reply-received` with `{ gmail_message_id, reply_text, received_at }`.
   - **Slack: Notify** — channel `#sales-replies`, with a preview snippet.
4. **Log** — append a row to a "Reply Activity" Google Sheet.

---

## 3. `followup_scheduler.json`

### Trigger
Schedule — daily at 09:00 server time.

### Nodes
1. **HTTP: Get follow-up candidates** — `GET /api/internal/leads-needing-followup`.
2. **For each lead:**
   - **HTTP: Trigger follow-up** — `POST /api/internal/trigger-followup`, body `{ "lead_id": ... }`.
   - **IF** response `should_send == true`:
     - **Gmail: Send** with returned `subject`/`body`.
     - **HTTP: Mark sent** — same as in `campaign_launcher`.
   - **ELSE** branch — just log.
3. **Google Sheets: append** — daily summary row.

---

## Cross-cutting notes
- The FastAPI `/api/internal/*` namespace is the contract between n8n and the rest of the system. Treat it as semi-public — version any breaking change.
- Avoid n8n "Function" / "Code" nodes that do business logic. If you find yourself writing JS inside n8n beyond simple mapping, move it to FastAPI.
- For idempotency, every n8n HTTP call to FastAPI carries an `Idempotency-Key` header (the n8n execution ID).
