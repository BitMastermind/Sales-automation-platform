# AI Sales Outreach Automation — Portfolio Overview

> A full-stack, production-grade B2B sales automation platform powered by LangGraph AI agents, FastAPI, and Next.js. Built to demonstrate senior-level architectural thinking across AI, backend, automation, and modern frontend.

---

## What It Does

This platform automates the entire B2B outbound sales cycle:

1. **Ingest leads** from CSV or Google Sheets
2. **Research each company** automatically (website, news, tech stack)
3. **Generate hyper-personalized cold emails** using AI — referencing specific, real facts about the company
4. **Send emails** via Gmail with built-in rate limiting and compliance checks
5. **Monitor for replies** every 15 minutes and classify intent (interested, meeting request, unsubscribe, etc.)
6. **Schedule intelligent follow-ups** at Day 3, Day 7, and Day 14 — each with a different strategy
7. **Sync status back** to the CRM and dashboard in real time

The core product value is **personalization quality** — not just "AI agents." Every email must reference a verifiable fact from the research data, and a compliance gate strips spam words, caps length, and validates claims before anything is sent.

---

## Architecture

```
Next.js (UI)  →  FastAPI (API)  →  LangGraph (reasoning)  →  n8n (automation)  →  External APIs
                      │                                                           (Gmail, HubSpot,
                      ▼                                                            Slack, Sheets)
             PostgreSQL + Qdrant + Redis
```

The system is split into three independent planes:

| Plane | Technology | Responsibility |
|-------|-----------|----------------|
| **Interaction** | Next.js 14 + FastAPI | UI, form handling, API, auth, webhooks |
| **Reasoning** | LangGraph + Claude + GPT-4o-mini | All LLM calls, prompts, retries, structured output |
| **Automation** | n8n (self-hosted) | Email sending, cron scheduling, Gmail monitoring, CRM sync |

> **Mental model:** n8n is the *pipeline*, LangGraph is the *brain*. No business logic leaks into n8n. No LLM calls leak into FastAPI.

This separation means each layer is independently replaceable and testable — a pattern that matters in production.

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui, TanStack Query |
| Backend | FastAPI, Python 3.11, SQLAlchemy 2.0 (async), Alembic, Pydantic v2 |
| AI Agents | LangGraph, LangChain, Anthropic Claude (Sonnet), OpenAI GPT-4o-mini |
| Automation | n8n (self-hosted via Docker) |
| Databases | PostgreSQL 15, Qdrant (vector store), Redis (rate limits + queues) |
| Infrastructure | Docker Compose, nginx, multi-stage Dockerfiles |

---

## AI Agents (LangGraph)

Four specialized agents, each with its own graph, Pydantic state schema, and isolated prompt files:

### 1. Research Agent
**`agents/research_agent.py`**

Nodes: `fetch_website → search_news → extract_tech_stack → synthesize → check_quality`

- Scrapes the company website via Firecrawl, searches for recent news via Tavily, infers tech stack from meta tags and job postings
- Claude synthesizes a structured JSON output with `industry`, `pain_points`, `recent_news`, `tech_stack`, `research_summary`
- GPT-4o-mini quality-gates the summary (≥ 50 words); loops back to synthesize up to 2 times if it fails

### 2. Personalization Agent (with embedded Compliance)
**`agents/personalization_agent.py`**

Nodes: `retrieve_templates → draft_email → compliance_check → refine`

- Retrieves the best-performing email templates from Qdrant, filtered by `industry` and `pain_point`
- Claude drafts the email few-shot from those templates, constrained to ≤ 150 words, no buzzwords, one specific company fact required
- GPT-4o-mini compliance gate blocks: spam words, unverified ROI claims, subject > 60 chars, body > 200 words
- Loops for up to 2 refinement passes on compliance failure

### 3. Reply Classifier
**`agents/reply_classifier.py`**

Single GPT-4o-mini structured-output call. Classifies inbound replies as:
`interested | not_interested | meeting_request | unsubscribe | needs_more_info | unknown`

Returns `intent`, `confidence`, `suggested_next_action`, and `key_phrases`.

### 4. Follow-up Agent
**`agents/followup_agent.py`**

A conditional LangGraph graph with time-aware strategy selection:

| Days since last touch | Strategy |
|----------------------|----------|
| 3 | Short bump — 2 sentences, references original email |
| 7 | Value-add — shares a relevant insight or resource |
| 14 | Break-up — "should I close your file?" |
| > 14 | Returns `{should_send: false}` — stops the sequence |

Reads prior follow-ups from the DB to avoid repeating angles.

---

## Backend (FastAPI)

- **12 REST endpoints** covering campaigns, leads, emails, webhooks, and Gmail OAuth
- **Gmail OAuth 2.0** — tokens stored encrypted in Postgres, auto-refresh on expiry, 100 emails/day rate limit enforced via Redis
- **Consistent response shape** across all endpoints: `{ "data": ..., "error": null, "meta": {...} }`
- **Internal trigger routes** (`/api/internal/trigger-research`, `trigger-personalization`, `trigger-followup`) called by n8n — cleanly separates automation triggers from public API
- **Webhook receivers** for n8n reply events and email open tracking

---

## Automation (n8n)

Three workflows, all stateless HTTP orchestration — no business logic:

| Workflow | Trigger | What it does |
|----------|---------|--------------|
| `campaign_launcher.json` | Webhook from FastAPI | Iterates leads, calls research + personalization + send; 30s rate limit between leads |
| `gmail_reply_monitor.json` | Cron every 15 min | Searches Gmail for replies, POSTs to `/webhooks/reply-received`, notifies Slack |
| `followup_scheduler.json` | Cron daily at 09:00 | Fetches follow-up candidates, triggers Follow-up Agent, logs to Google Sheets |

---

## Database Design

**PostgreSQL** (source of truth):
- `campaigns` — campaign config and status
- `leads` — contact info, status enum (`new → researched → emailed → replied → converted`), `research_data` JSONB
- `emails` — full email record with sent/opened/replied timestamps
- `replies` — inbound replies with `classified_as` enum
- `crm_updates` — CRM sync log (HubSpot-ready payload)
- `oauth_tokens` — encrypted Gmail tokens with auto-refresh

**Qdrant** (vector memory):
- `company_research` — embeddings of research summaries, enables "find similar companies"
- `email_templates` — embeddings of winning emails indexed by `industry + pain_point`, retrieves the best templates per lead

**Redis** — Gmail send rate counters, short-lived locks

---

## Frontend (Next.js 14)

Pages: `/dashboard`, `/campaigns`, `/campaigns/[id]`, `/settings`

- **Campaign creation** — three-step wizard: campaign basics → CSV lead upload with column mapping → review & launch
- **Lead detail view** — full email history, reply classification, follow-up status
- **Stats dashboard** — email open rates, reply rates, conversion funnel (Recharts)
- Data fetching via TanStack Query — no Redux/Zustand

---

## Build Progress

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Project scaffold, Docker skeleton, Makefile | ✅ Complete |
| 1 | PostgreSQL schema, Alembic migrations, Qdrant collections | ✅ Complete |
| 2 | FastAPI routes, Gmail OAuth + GmailService | ✅ Complete |
| 3 | All 4 LangGraph agents (Research, Personalization, Reply, Follow-up) — 81 tests passing | ✅ Complete |
| 4 | n8n workflows (launcher, reply monitor, follow-up scheduler) | ✅ Complete |
| 5 | Next.js frontend (dashboard, campaign wizard, lead detail) | ✅ Complete |
| 6 | End-to-end integration test suite | ⬜ In queue |
| 7 | Full Docker Compose deploy | ⬜ In queue |

---

## What Makes This Senior-Level Work

- **Strict layer separation** — reasoning never leaks into automation, LLM calls never happen in FastAPI. Each layer is independently testable and swappable.
- **Structured output everywhere** — agents return Pydantic-validated JSON. Bad output → `AgentOutputError` → clean 422 response, never an opaque 500.
- **Compliance gate built into the AI pipeline** — the system can't send spam words or unverified claims by design, not by convention.
- **Exponential backoff on transient model errors** — with explicit separation from validation failures (never silently retried).
- **Vector memory for personalization quality** — winning templates are stored and retrieved by relevance, so email quality improves as campaigns run.
- **Async throughout** — FastAPI + SQLAlchemy 2.0 async, `asyncio`-native LangGraph agents, Redis for rate limiting under load.
- **81 tests passing** on the agent layer alone, with a smoke script that runs all agents against a live fixture.

---

## Running Locally

```bash
cp .env.example .env        # Fill in API keys
docker compose up --build   # All services start healthy
make migrate                # Apply DB schema
make seed                   # Seed demo campaign + leads
# Visit http://localhost:3000
```

Required keys: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `TAVILY_API_KEY`, `FIRECRAWL_API_KEY`

---

## Key Design Decisions

| Decision | Reason |
|----------|--------|
| n8n for automation, not custom schedulers | Gives visual debugging, built-in retry, and Gmail/Sheets nodes out of the box |
| LangGraph instead of plain LLM calls | Graph structure enforces the quality loop — research can't skip the quality gate |
| Qdrant for template retrieval | Semantic search by `industry + pain_point` outperforms SQL filtering for relevance |
| Claude for synthesis, GPT-4o-mini for checks | Claude handles nuanced writing; GPT-4o-mini is fast and cheap for boolean quality gates |
| No mocks in integration tests | Real Postgres test container — mock/prod divergence has burned too many projects |
