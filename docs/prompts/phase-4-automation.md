# Phase 4 — n8n Automation Workflows

> n8n is the pipeline, not the brain. Every reasoning step is an HTTP call. Keep nodes simple.

---

## Session Setup

| | |
|---|---|
| **Model** | `claude-sonnet-4-6` |
| **Skills** | None required — this is a specification/JSON generation task |
| **Depends on** | Phase 2 complete (FastAPI `/api/internal/*` routes working) |
| **Estimated time** | 60–90 min |

---

#### ROLE & PERSONA

You are a senior automation engineer with deep expertise in n8n workflow design, Gmail API integration, and webhook-driven pipeline architecture. You have built production n8n workflows for B2B sales systems and know how to structure node connections, error handling, and credential references in n8n's JSON export format.

---

#### TASK & OBJECTIVE

Generate three production-ready n8n workflow JSON export files (`campaign_launcher.json`, `gmail_reply_monitor.json`, `followup_scheduler.json`), a credentials reference doc, and an updated README — all importable into n8n with correct node structure, credentials references by name, and error routing on every HTTP node.

---

#### MY SITUATION

Phase 2 is complete — all `/api/internal/*` FastAPI routes are live and responding. n8n is running in Docker on `http://localhost:5678` (external) and `http://n8n:5678` (internal Docker network). The FastAPI backend is at `http://backend:8000` inside Docker. The `/api/internal` routes require header `X-Internal-Token: <INTERNAL_API_TOKEN from env>`. Gmail, Slack, and Google Sheets credentials will be configured in the n8n UI by name — they are not embedded in the JSON.

---

#### CONSTRAINTS

- Do **not** embed credentials, API keys, or tokens in the JSON files — reference by credential name only.
- All internal API calls must include an `Idempotency-Key` header formatted as `{{ $execution.id }}-<step>-{{ $json.id }}`.
- **Every HTTP node's error output** must connect to the Slack error notification node.
- Do **not** use n8n "Code" or "Function" nodes for business logic — only HTTP calls to the backend.
- The Gmail node must use the `"Gmail Account"` credential by name — not inline OAuth.
- Webhook paths must follow the pattern `/webhook/<workflow-name>`.

---

#### AUDIENCE FOR THE OUTPUT

These JSON files are imported into n8n by the operator during deployment (Phase 7). They are also reviewed by backend engineers to understand the trigger flow. The JSON must be valid n8n export format — parseable by n8n's import tool — and the node names/paths must match what the FastAPI backend expects.

---

#### PRIOR ATTEMPTS / WHAT FAILED

- Do not use n8n "Function" nodes to parse JSON responses — the HTTP Request node returns parsed JSON automatically.
- Do not hardcode `INTERNAL_API_TOKEN` in the JSON — use `{{ $env.INTERNAL_API_TOKEN }}` expression.
- Do not connect the "true" branch of IF nodes to the Slack error node — errors only come from HTTP node error outputs.
- The Gmail "GetAll" operation returns an array — always feed it into Split In Batches before processing individual messages.

---

#### FORMAT

Deliver files in this order:
1. `/n8n-workflows/campaign_launcher.json` — complete n8n export JSON
2. `/n8n-workflows/gmail_reply_monitor.json` — complete n8n export JSON
3. `/n8n-workflows/followup_scheduler.json` — complete n8n export JSON
4. `/n8n-workflows/CREDENTIALS.md` — credential setup reference
5. `/n8n-workflows/README.md` update — append "Setup Order" section
6. Verify steps (manual n8n import checks).

---

#### TONE & EXPERTISE LEVEL

Expert. n8n JSON node format, expression syntax (`{{ $json.field }}`), and credential-by-name referencing assumed known.

---

#### THINKING INSTRUCTION

Before writing the `campaign_launcher.json`, trace the full data flow: what shape does the Webhook receive? What shape does each subsequent HTTP response have? What field names does the Gmail node receive from the personalization endpoint? Map each `{{ $json.field }}` expression to its source node before writing the JSON. Flag any shape mismatch between what the personalization endpoint returns and what the Gmail node expects.

---

#### DETAILED SPEC

**n8n JSON format notes:**
- Each workflow: `{ id, name, nodes: [...], connections: {...}, settings: {} }`
- Node types: `n8n-nodes-base.webhook`, `n8n-nodes-base.scheduleTrigger`, `n8n-nodes-base.httpRequest`, `n8n-nodes-base.gmail`, `n8n-nodes-base.slack`, `n8n-nodes-base.googleSheets`, `n8n-nodes-base.splitInBatches`, `n8n-nodes-base.wait`, `n8n-nodes-base.if`, `n8n-nodes-base.noOp`
- Credentials referenced by name, never embedded.

---

**Workflow 1 — `campaign_launcher.json`**

Trigger: Webhook, `POST /webhook/campaign-launcher`, responds with "Last Node".
Input: `{ "campaign_id": "<uuid>" }`

Node sequence:
1. **Webhook** — receives `campaign_id`
2. **HTTP Request — Fetch Leads** — `GET http://backend:8000/api/internal/leads?campaign_id={{ $json.body.campaign_id }}&status=new`, header `X-Internal-Token: {{ $env.INTERNAL_API_TOKEN }}`
3. **Split In Batches** — size: 1, iterates `data` array
4. **HTTP Request — Trigger Research** — `POST http://backend:8000/api/internal/trigger-research`, body: `{ "lead_id": "{{ $json.id }}" }`, idempotency key: `{{ $execution.id }}-research-{{ $json.id }}`
5. **HTTP Request — Trigger Personalization** — `POST http://backend:8000/api/internal/trigger-personalization`, body: `{ "lead_id": "{{ $json.lead_id }}" }`, idempotency key: `{{ $execution.id }}-personalization-{{ $json.lead_id }}`
6. **Gmail Node — Send Email** — credential: "Gmail Account", operation: Send, to: `{{ $json.data.lead_email }}`, subject: `{{ $json.data.subject }}`, message: `{{ $json.data.full_email }}`
7. **HTTP Request — Mark Sent** — `PATCH http://backend:8000/api/internal/emails/{{ $json.data.email_id }}/sent`, body: `{ "gmail_message_id": "{{ $json.messageId }}" }`
8. **Wait Node** — 30 seconds (rate limiting between leads)
9. **Slack Node (error handler)** — on any HTTP node error output, post to `#sales-errors`: `"Campaign launcher error for campaign {{ $('Webhook').item.json.body.campaign_id }}: {{ $json.message }}"`

---

**Workflow 2 — `gmail_reply_monitor.json`**

Trigger: Schedule Trigger, every 15 minutes.

Node sequence:
1. **Schedule Trigger**
2. **HTTP Request — Get Sent Email IDs** — `GET http://backend:8000/api/internal/sent-emails/recent?days=14`, returns `{ data: [{ gmail_message_id, email_id }] }`
3. **Gmail Node — Search Replies** — operation: GetAll, query: `"is:inbox newer_than:15m"`, limit: 50
4. **IF Node — Filter** — condition: process all inbox messages newer than 15 min (MVP: no threadId filter yet)
5. **Split In Batches** — size: 1
6. **Gmail Node — Get Full Message** — operation: Get, message ID: `{{ $json.id }}`
7. **HTTP Request — POST Reply Webhook** — `POST http://backend:8000/api/webhooks/n8n/reply-received`, body: `{ "gmail_message_id": "{{ $json.id }}", "reply_text": "<decoded body>", "received_at": "{{ $json.internalDate | toDateTime }}" }`
8. **Slack Node — Notify on Interest** — only if `classified_as` is `"interested"` or `"meeting_request"`, post to `#sales-replies`: `"Reply from {{ $json.from }}: {{ $json.snippet }}"`
9. **Google Sheets Node — Log Run** — operation: Append, sheet: "Reply Monitor Log", columns: timestamp, messages_checked, replies_found, errors

---

**Workflow 3 — `followup_scheduler.json`**

Trigger: Schedule Trigger, daily at 09:00 local server time.

Node sequence:
1. **Schedule Trigger**
2. **HTTP Request — Get Follow-up Candidates** — `GET http://backend:8000/api/internal/leads-needing-followup`, header `X-Internal-Token: {{ $env.INTERNAL_API_TOKEN }}`
3. **IF Node — Any Leads?** — condition: `{{ $json.data.length }} > 0`. True → continue. False → Sheets log.
4. **Split In Batches** — size: 1
5. **HTTP Request — Trigger Follow-up** — `POST http://backend:8000/api/internal/trigger-followup`, body: `{ "lead_id": "{{ $json.lead_id }}" }`
6. **IF Node — Should Send?** — condition: `{{ $json.data.should_send }} === true`. True → Gmail. False → Sheets log.
7. **Gmail Node — Send Follow-up** — credential: "Gmail Account", to: `{{ $json.data.lead_email }}`, subject: `{{ $json.data.subject }}`, message: `{{ $json.data.body }}`
8. **HTTP Request — Mark Follow-up Sent** — `PATCH http://backend:8000/api/internal/emails/{{ $json.data.email_id }}/sent`, body: `{ "gmail_message_id": "{{ $json.messageId }}" }`
9. **Google Sheets Node — Daily Summary** — Append: `{ date, leads_processed, followups_sent, stopped }`

---

**`/n8n-workflows/CREDENTIALS.md`** — list all 4 credentials needed and where to set them in the n8n UI:
- **Gmail OAuth2** (name: "Gmail Account") — Settings → Credentials → OAuth2 → Gmail
- **Slack API** (name: "Slack Account") — Bot token with `chat:write` scope
- **Google Sheets OAuth2** (name: "Google Sheets Account")
- **HTTP Header Auth** (name: "FastAPI Internal") — Header: `X-Internal-Token`, Value: from `.env`

**`/n8n-workflows/README.md`** — append "Setup Order" section:
1. Import `campaign_launcher.json` (start inactive)
2. Import `gmail_reply_monitor.json` (start inactive)
3. Import `followup_scheduler.json` (start inactive)
4. Configure all credentials (see CREDENTIALS.md)
5. Activate `gmail_reply_monitor` first (safest — read-only)
6. Activate `followup_scheduler`
7. Test `campaign_launcher` manually before activating

**Verify:**
```
1. make dev  (boots n8n at localhost:5678)
2. Import campaign_launcher.json via n8n UI → confirm nodes appear
3. Import gmail_reply_monitor.json → confirm it parses
4. Import followup_scheduler.json → confirm it parses
5. Execute campaign_launcher manually: body { "campaign_id": "00000000-0000-0000-0000-000000000001" }
   Expected: HTTP 404 from backend (no such campaign) — workflow runs to error handler without crashing
```

---

## After Phase 4

1. All three workflows import cleanly into n8n.
2. Note in `scratchpad.md`: any n8n JSON schema quirks, credentials that needed re-naming.
3. Commit the JSON files.
4. Open Phase 5 (Frontend) in a new session.
