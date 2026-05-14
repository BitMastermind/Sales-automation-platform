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

## Prompt

```
Read CLAUDE.md before starting.

## Context
Phase 4: generate the three n8n workflow JSON export files and their documentation.
n8n is running locally on http://localhost:5678 (via Docker Compose from Phase 0).
The FastAPI backend is on http://backend:8000 inside Docker, or http://localhost:8000 from outside.
Internal API calls require header: X-Internal-Token: <value from env INTERNAL_API_TOKEN>

## What you need to know about n8n JSON format
- Each workflow is an object with: id, name, nodes (array), connections (object), settings.
- Node types used here: n8n-nodes-base.webhook, n8n-nodes-base.scheduleTrigger,
  n8n-nodes-base.httpRequest, n8n-nodes-base.gmail, n8n-nodes-base.slack,
  n8n-nodes-base.googleSheets, n8n-nodes-base.splitInBatches, n8n-nodes-base.wait,
  n8n-nodes-base.if, n8n-nodes-base.noOp
- Credentials are referenced by name (set in n8n UI), not embedded in JSON.
- Webhook paths should be: /webhook/<workflow-name>

## Task 1 — campaign_launcher.json

Create /n8n-workflows/campaign_launcher.json

Trigger: Webhook node
  - HTTP Method: POST
  - Path: /campaign-launcher
  - Responds with: "Last Node" (so it returns the final HTTP response)

Nodes in order:
1. Webhook (trigger)
   Input: { "campaign_id": "<uuid>" }

2. HTTP Request — Fetch Leads
   Method: GET
   URL: http://backend:8000/api/internal/leads?campaign_id={{ $json.body.campaign_id }}&status=new
   Headers: { "X-Internal-Token": "{{ $env.INTERNAL_API_TOKEN }}" }
   Output: { data: [{ id, company_name, email }] }

3. Split In Batches
   Batch size: 1
   Iterates over data array from step 2.

4. HTTP Request — Trigger Research
   Method: POST
   URL: http://backend:8000/api/internal/trigger-research
   Headers: { "X-Internal-Token": "...", "Idempotency-Key": "{{ $execution.id }}-research-{{ $json.id }}" }
   Body: { "lead_id": "{{ $json.id }}" }

5. HTTP Request — Trigger Personalization
   Method: POST
   URL: http://backend:8000/api/internal/trigger-personalization
   Headers: { "X-Internal-Token": "...", "Idempotency-Key": "{{ $execution.id }}-personalization-{{ $json.lead_id }}" }
   Body: { "lead_id": "{{ $json.lead_id }}" }

6. Gmail Node — Send Email
   Credentials: Gmail OAuth2 (named "Gmail Account" in n8n)
   Operation: Send
   To: {{ $json.data.lead_email }}
   Subject: {{ $json.data.subject }}
   Message: {{ $json.data.full_email }}
   (The personalization endpoint returns { data: { lead_email, subject, full_email, email_id } })

7. HTTP Request — Mark Sent
   Method: PATCH
   URL: http://backend:8000/api/internal/emails/{{ $json.data.email_id }}/sent
   Headers: { "X-Internal-Token": "..." }
   Body: { "gmail_message_id": "{{ $json.messageId }}" }

8. Wait Node
   Amount: 30 seconds
   (Rate limit between leads)

Error handling: On any HTTP node failure → connect error output to a Slack notification node.
Slack node (on error): Post to channel #sales-errors with message:
  "Campaign launcher error for campaign {{ $('Webhook').item.json.body.campaign_id }}: {{ $json.message }}"

## Task 2 — gmail_reply_monitor.json

Create /n8n-workflows/gmail_reply_monitor.json

Trigger: Schedule Trigger
  Rule: Every 15 minutes

Nodes in order:
1. Schedule Trigger

2. HTTP Request — Get Sent Email IDs
   Method: GET
   URL: http://backend:8000/api/internal/sent-emails/recent?days=14
   Headers: { "X-Internal-Token": "..." }
   Output: { data: [{ gmail_message_id, email_id }] }

3. Gmail Node — Search Replies
   Operation: GetAll
   Filters: Query: "is:inbox newer_than:15m"
   Limit: 50
   (Returns array of Gmail message objects with: id, threadId, snippet, internalDate)

4. IF Node — Filter: only replies to our sent emails
   Condition: The Gmail threadId exists in a thread we track.
   (For MVP, process all inbox messages newer than 15min — Phase 6 can tighten this)

5. For each new message (via Split In Batches, size: 1):
   a. Gmail Node — Get Full Message
      Operation: Get
      Message ID: {{ $json.id }}
      Output includes: payload.body.data (base64 body)

   b. HTTP Request — POST to webhook
      Method: POST
      URL: http://backend:8000/api/webhooks/n8n/reply-received
      Body: {
        "gmail_message_id": "{{ $json.id }}",
        "reply_text": "<decoded body>",
        "received_at": "{{ $json.internalDate | toDateTime }}"
      }

   c. Slack Node — Notify (only if backend returned 200 and classified_as is "interested" or "meeting_request")
      Channel: #sales-replies
      Message: "Reply from {{ $json.from }}: {{ $json.snippet }}"

6. Google Sheets Node — Log Run
   Operation: Append
   Sheet: "Reply Monitor Log"
   Columns: timestamp, messages_checked, replies_found, errors

## Task 3 — followup_scheduler.json

Create /n8n-workflows/followup_scheduler.json

Trigger: Schedule Trigger
  Rule: Daily at 09:00 (local server time)

Nodes in order:
1. Schedule Trigger

2. HTTP Request — Get Follow-up Candidates
   Method: GET
   URL: http://backend:8000/api/internal/leads-needing-followup
   Headers: { "X-Internal-Token": "..." }
   Output: { data: [{ lead_id, days_since_sent }] }

3. IF Node — Any leads to process?
   Condition: {{ $json.data.length }} > 0
   True branch → continue
   False branch → Google Sheets log (no-op)

4. Split In Batches (size: 1) — iterate over leads

5. HTTP Request — Trigger Follow-up
   Method: POST
   URL: http://backend:8000/api/internal/trigger-followup
   Headers: { "X-Internal-Token": "..." }
   Body: { "lead_id": "{{ $json.lead_id }}" }

6. IF Node — Should Send?
   Condition: {{ $json.data.should_send }} === true
   True → Gmail Send node
   False → Sheets log only

7. Gmail Node — Send Follow-up (true branch)
   Same credential as campaign_launcher.
   To: {{ $json.data.lead_email }}
   Subject: {{ $json.data.subject }}
   Message: {{ $json.data.body }}

8. HTTP Request — Mark Follow-up Sent (after Gmail)
   Method: PATCH
   URL: http://backend:8000/api/internal/emails/{{ $json.data.email_id }}/sent
   Body: { "gmail_message_id": "{{ $json.messageId }}" }

9. Google Sheets Node — Daily Summary
   Append row: { date, leads_processed, followups_sent, stopped }

## Task 4 — n8n credentials reference

Create /n8n-workflows/CREDENTIALS.md:
  List all credentials needed and where to set them in the n8n UI:
  - Gmail OAuth2 (name: "Gmail Account") — Settings → Credentials → OAuth2 → Gmail
  - Slack API (name: "Slack Account") — Bot token with chat:write scope
  - Google Sheets OAuth2 (name: "Google Sheets Account")
  - HTTP Header Auth (name: "FastAPI Internal") — Header: X-Internal-Token, Value: from .env

## Task 5 — Update /n8n-workflows/README.md
Append a "Setup Order" section:
  1. Import campaign_launcher.json (start inactive)
  2. Import gmail_reply_monitor.json (start inactive)
  3. Import followup_scheduler.json (start inactive)
  4. Configure all credentials (see CREDENTIALS.md)
  5. Activate gmail_reply_monitor first (safest — read-only)
  6. Activate followup_scheduler
  7. Test campaign_launcher manually before activating

## Constraints
- Do NOT embed credentials, API keys, or tokens in the JSON files.
- All internal API calls must include the Idempotency-Key header.
- Error outputs on HTTP nodes must connect to the Slack error notification node.
- Do NOT use n8n "Code" or "Function" nodes for business logic — only HTTP calls.
- The Gmail node must use the "Gmail Account" credential by name (not inline OAuth).

## Verify
1. Run: make dev (boots n8n at localhost:5678)
2. Import campaign_launcher.json via n8n UI → confirm it parses and nodes appear.
3. Import gmail_reply_monitor.json → confirm it parses.
4. Import followup_scheduler.json → confirm it parses.
5. In n8n, execute campaign_launcher manually with body: { "campaign_id": "00000000-0000-0000-0000-000000000001" }
   Expected: HTTP request to backend 404 (no such campaign) — workflow runs to error handler without crashing.

Update CLAUDE.md: Phase 4 → ✅ complete.
```

---

## After Phase 4
1. All three workflows import cleanly into n8n.
2. Note in `scratchpad.md`: any n8n JSON schema quirks, credentials that needed re-naming.
3. Commit the JSON files.
4. Open Phase 5 (Frontend) in a new session.
