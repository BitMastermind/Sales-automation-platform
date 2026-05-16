# /n8n-workflows — Automation Pipelines

Exported n8n JSON files. n8n handles HTTP, Gmail, Slack, Sheets, and CRM sync. It does **not** reason — every reasoning step is an HTTP call to FastAPI which in turn calls a LangGraph agent.

## Workflows
| File | Trigger | Purpose |
|------|---------|---------|
| `campaign_launcher.json` | Webhook from FastAPI | Iterate leads, trigger research + email per lead with rate limit |
| `gmail_reply_monitor.json` | Cron (every 15 min) | Search Gmail for replies, POST to `/api/webhooks/reply-received`, Slack alert |
| `followup_scheduler.json` | Cron (daily 09:00) | Fetch leads needing follow-up, trigger follow-up agent, log to Sheets |

Detailed node-level spec: [../docs/05-N8N-WORKFLOWS.md](../docs/05-N8N-WORKFLOWS.md)

## Importing
1. Boot the stack: `make dev` (n8n runs on `http://localhost:5678`)
2. n8n UI → Workflows → Import from file → pick a JSON file here.
3. Set credentials inside n8n (Gmail OAuth, Slack token, internal FastAPI base URL).
4. Activate the workflow.

## Rules
- Workflows must be **pure orchestration**. No code nodes that reach into LLM APIs directly.
- Every workflow's webhook URL is set via `N8N_WEBHOOK_URL` env, not hardcoded.
- After editing in the UI, re-export the JSON and commit it.

## Setup Order
1. Import `campaign_launcher.json` (start inactive)
2. Import `gmail_reply_monitor.json` (start inactive)
3. Import `followup_scheduler.json` (start inactive)
4. Configure all credentials (see `CREDENTIALS.md`)
5. Activate `gmail_reply_monitor` first (read-only)
6. Activate `followup_scheduler`
7. Test `campaign_launcher` manually before activating
