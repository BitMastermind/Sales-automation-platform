# 00 — Architecture

## Mental Model
> Don't think "one huge AI app". Think "orchestrate multiple systems".

Three planes:
1. **Interaction plane** — Next.js dashboard + FastAPI API. Where humans + external services meet the system.
2. **Reasoning plane** — LangGraph agents. Every LLM call lives here. The backend never imports `openai` or `anthropic` directly.
3. **Automation plane** — n8n workflows. Orchestrates Gmail, Slack, Sheets, CRM. Stateless; only HTTP nodes.

The split exists so each layer can be replaced. Swap n8n for Temporal, swap LangGraph for a custom DAG — neither leaks into the other.

## End-to-End Flow

```
┌─────────────┐
│  Frontend   │  User creates campaign + uploads CSV
│  (Next.js)  │
└──────┬──────┘
       │ HTTPS
       ▼
┌─────────────┐
│   FastAPI   │  Validates + persists; triggers automation
│   Backend   │
└──────┬──────┘
       │ webhook
       ▼
┌─────────────┐
│     n8n     │  Iterates leads, calls FastAPI per lead
│  Workflows  │  (rate-limited)
└──────┬──────┘
       │ HTTP
       ▼
┌─────────────┐
│  FastAPI    │  /internal/trigger-research
│  /internal  │
└──────┬──────┘
       │
       ▼
┌─────────────┐         ┌──────────┐
│  LangGraph  │ ◄──────►│  Qdrant  │  memory + templates
│   Agents    │         └──────────┘
└──────┬──────┘
       │ structured JSON
       ▼
┌─────────────┐
│   FastAPI   │  persists email + returns to n8n
└──────┬──────┘
       │
       ▼
┌─────────────┐
│     n8n     │  → Gmail send
│ Gmail Node  │  → Slack notify
└─────────────┘

         ─── 15 min later ───

┌─────────────┐
│     n8n     │  Cron: scans Gmail for replies
│ Reply Watch │  POST /api/webhooks/reply-received
└──────┬──────┘
       ▼
┌─────────────┐
│  LangGraph  │  Reply Classifier
│   Agents    │  → updates lead status, syncs CRM
└─────────────┘
```

## Component Responsibilities

| Component | Owns | Does NOT own |
|-----------|------|--------------|
| Next.js | UI, form validation, OAuth redirects | Business rules, persistence |
| FastAPI | Persistence, validation, auth, webhooks, agent invocation | Direct LLM calls, email sending, CRM API calls |
| LangGraph | All reasoning, prompt engineering, retries on bad output | HTTP routing, DB writes |
| n8n | Triggers, schedules, Gmail/Slack/Sheets/CRM I/O | Decisions, transformations beyond mapping |
| Postgres | Source of truth: campaigns, leads, emails, replies | Search ranking, semantic memory |
| Qdrant | Vector memory: company research, winning email templates | Relational data |
| Redis | Rate limits, ephemeral counters, short-lived locks | Anything that needs to survive a restart |

## Why this split makes the project look senior
- **Retries, async, webhooks, queues, structured outputs, analytics, auth, integrations.** Those are the things hiring managers and clients notice. The "AI" is the easy part.
- Each plane is independently testable.
- The reasoning layer is decoupled from the wire format, so prompts evolve without API breakage.

## Data Flow Details
- **Inbound leads** → CSV parsed in backend, validated, bulk-inserted with `status='new'`.
- **Research** → Research Agent enriches `leads.research_data` (JSONB) and upserts a Qdrant vector keyed by `lead_id`.
- **Email draft** → Personalization Agent retrieves top templates from Qdrant by `industry+pain_point`, produces final email, runs Compliance gate, persists to `emails` table.
- **Send** → n8n's Gmail node sends; `messageId` is stored back via webhook.
- **Reply** → Gmail Reply Monitor cron finds it, calls webhook, Reply Classifier sets `replies.classified_as`, frontend reflects the new state on next refresh.
- **Follow-up** → Cron at 09:00 finds leads with no reply for 3/7/14 days, calls Follow-up Agent, which emits a context-aware new email or `{should_send: false}`.

## See Also
- Phase-by-phase build plan: [01-PHASES.md](01-PHASES.md)
- Database schema: [02-DATABASE.md](02-DATABASE.md)
- Agent specs: [03-AGENTS.md](03-AGENTS.md)
