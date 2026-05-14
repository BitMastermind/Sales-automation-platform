# 03 — LangGraph Agents

Five agents. Each owns a file under `/agents/`, exposes a single async entry point, and uses Pydantic for its state schema. The backend talks to agents through `/backend/agents_interface/` only.

## Agent Catalogue

| Agent | Entry point | Primary model |
|-------|-------------|---------------|
| Research | `agents/research_agent.py` → `run_research_agent(lead)` | Claude `claude-sonnet-4-20250514` (synthesis) + `gpt-4o-mini` (quality) |
| Personalization | `agents/personalization_agent.py` → `run_personalization_agent(lead, research, campaign_context)` | Claude `claude-sonnet-4-20250514` |
| Compliance | merged into Personalization graph | `gpt-4o-mini` |
| Reply Classifier | `agents/reply_classifier.py` → `run_reply_classifier(reply_text)` | `gpt-4o-mini` |
| Follow-up | `agents/followup_agent.py` → `run_followup_agent(lead_id, db_session)` | Claude `claude-sonnet-4-20250514` |

---

## 1. Research Agent

### Goal
Given `{company_name, website}`, return structured research used downstream for personalization.

### State (Pydantic / TypedDict)
```python
class ResearchState(TypedDict):
    lead: dict
    raw_website: str | None
    news: list[dict]
    tech_stack: list[str]
    output: dict | None      # final synthesised JSON
    quality_ok: bool
    refine_count: int
```

### Graph
```
START
  ▼
fetch_website          (Firecrawl or httpx + BeautifulSoup)
  ▼
search_news            (Tavily)
  ▼
extract_tech_stack     (meta tags, job postings hint)
  ▼
synthesize             (Claude — produces structured output)
  ▼
check_quality          (gpt-4o-mini — research_summary >= 50 words?)
  │
  ├─ ok ──► END
  └─ no ──► back to synthesize (max 2 retries)
```

### Output Schema
```json
{
  "industry": "Logistics SaaS",
  "company_size": "50-200",
  "pain_points": ["manual operations", "outbound scaling"],
  "recent_news": ["expanded to Europe Q1"],
  "tech_stack": ["Salesforce", "Outreach.io"],
  "research_summary": "ABC Logistics is a mid-size logistics SaaS firm expanding into Europe; outbound sales motion appears manual based on recent sales hires."
}
```

---

## 2. Personalization Agent (with embedded Compliance)

### Goal
Given research + campaign context, produce a single high-relevance email.

### State
```python
class PersonalizationState(TypedDict):
    lead: dict
    research: dict
    campaign_context: dict
    templates: list[dict]
    draft: dict | None
    compliance: dict | None     # {"pass": bool, "violations": [...]}
    refine_count: int
```

### Graph
```
START
  ▼
retrieve_templates     (Qdrant: get_best_templates(industry, pain_point))
  ▼
draft_email            (Claude — few-shot from templates)
  ▼
compliance_check       (gpt-4o-mini — spam words, length, false claims)
  │
  ├─ pass ──► END
  └─ fail ──► refine ──► compliance_check (max 2 iterations)
```

### Draft system prompt (load-bearing)
> "You write B2B cold emails. You are direct, specific, and never generic. Every email must reference one specific fact about the company. Max 150 words. No exclamation marks. No buzzwords."

### Compliance rules
- Disallow words: `guaranteed, free money, act now, limited time, click here`.
- No unverified claims about ROI, %, or named customers.
- Length: subject ≤ 60 chars, body ≤ 200 words.
- Personalization must reference a string also present in `research`.

### Output
```json
{
  "subject": "Question about your Europe expansion",
  "opening_line": "Saw your expansion into Europe — that usually 3x's outbound ops complexity.",
  "body": "...",
  "cta": "Open to a 15-min chat next Tuesday?",
  "full_email": "<assembled>"
}
```

---

## 3. Reply Classifier

### Goal
Classify an inbound reply so n8n can branch.

### Input
`reply_text: str`, optional `prior_email: str` for context.

### Output
```json
{
  "intent": "interested",
  "confidence": 0.86,
  "suggested_next_action": "schedule_call",
  "key_phrases": ["sounds interesting", "next week"]
}
```

Intents: `interested | not_interested | meeting_request | unsubscribe | needs_more_info | unknown`.

Single LLM call (`gpt-4o-mini`) with structured-output mode. No graph needed.

---

## 4. Follow-up Agent

### Goal
Generate a follow-up email *or* signal we should stop. Adapts to days elapsed and prior follow-ups.

### Logic (implemented as a LangGraph conditional graph)
| Days since last touch | Strategy |
|-----------------------|----------|
| 3 | Short bump — 2 sentences max, reference the original email |
| 7 | Value-add — share a relevant insight or resource |
| 14 | Break-up — "should I close your file?" |
| > 14 | Return `{"should_send": false}` |

Reads prior follow-ups for the lead so it never repeats an angle.

### Output
```json
{
  "should_send": true,
  "subject": "Quick bump on my last note",
  "body": "...",
  "strategy": "day_3_bump"
}
```

---

## Shared rules
- **Structured output mode** wherever the SDK supports it (OpenAI `response_format`, Anthropic tool-use).
- Every agent returns a Pydantic-validated dict. If validation fails twice → raise `AgentOutputError` (handled by the API layer with a 422 response, never an opaque 500).
- Retries: 3 with exponential backoff on transient model errors only — never silently retry validation failures.
- All prompts live in `/agents/prompts/*.py` so they can be diff-reviewed independently of code.

## Testing pattern
- Unit: mock the LLM (`respx` + canned JSON) — assert schema + edge cases.
- Integration: live LLM against a fixed input, snapshot the output (regen on prompt edits).
- Smoke: `/agents/scripts/smoke.py` runs each agent against a single fixture lead.
