# Phase 3 — LangGraph Agents

> This is the reasoning core. Use Opus. Take more time. Get it right.

---

## Session Setup

| | |
|---|---|
| **Model** | `claude-opus-4-7` |
| **Skills** | Invoke `brainstorming` first, then `test-driven-development` for each agent |
| **Depends on** | Phase 2 complete (backend routes working) |
| **Estimated time** | 2–3 hours across 3–4 sub-sessions |

> Each sub-phase (3A, 3B, 3C, 3D) is its own session. Don't combine them.
> Invoke `/skill brainstorming` at the start of each session — even if the spec is clear —
> because the brainstorm will surface edge cases you'd otherwise hit during implementation.

---

## Shared Context (paste at the start of every Phase 3 session)

```
Read CLAUDE.md before starting.

Key constraint for ALL agents:
- Every agent lives in /agents/ and exports a single async entry point.
- The backend calls agents through /backend/agents_interface/ — never importing from /agents/ directly.
- Agents return Pydantic-validated dicts. If validation fails twice → raise AgentOutputError.
- Prompts live in /agents/prompts/<agent_name>.py — never inline in the graph.
- Models: synthesis nodes use Claude claude-sonnet-4-20250514. Quality/classification nodes use gpt-4o-mini.
- All LLM calls use structured output mode (Anthropic tool-use or OpenAI response_format).
- Retry on transient model errors: 3 attempts with exponential backoff.
- Never retry silently on schema validation failure — surface it as AgentOutputError.
```

---

## Phase 3A — Research Agent

### Prompt

```
[Paste the shared context above first]

## Task: Research Agent
Location: /agents/research_agent.py
Prompts: /agents/prompts/research_prompts.py
Entry point: async def run_research_agent(lead: dict) -> dict

### LangGraph state: ResearchState (TypedDict)
  lead: dict                          # { company_name, website }
  raw_website_text: str | None
  news_results: list[dict]            # from Tavily
  tech_stack_hints: list[str]
  synthesized: dict | None            # LLM output
  quality_ok: bool
  refine_count: int                   # max 2

### Graph nodes (implement each as an async function, take state, return partial state):

1. fetch_website(state):
   Use httpx.AsyncClient to GET the lead's website.
   If the site loads: extract text from <p>, <h1>-<h3>, <meta description> using BeautifulSoup.
   Limit text to 3000 chars (truncate).
   If fetch fails (timeout 10s, any HTTP error): set raw_website_text = "" and log a warning.
   Do NOT raise — graceful degradation is correct here.

2. search_news(state):
   Call Tavily search API (async) with query: f"{state['lead']['company_name']} company news 2024 2025"
   max_results=5. Store in news_results.
   If Tavily key missing or API error: set news_results = [] and log warning.

3. extract_tech_stack(state):
   Simple heuristic extraction from raw_website_text + news content.
   Look for mentions of: Salesforce, HubSpot, Outreach, Gong, Slack, Notion, Jira, AWS, GCP, Azure.
   Return list of detected tools.

4. synthesize(state):
   Call Claude claude-sonnet-4-20250514 with tool_use structured output.
   Tool schema (the output format):
   {
     "industry": str,                        # e.g. "Logistics SaaS"
     "company_size": str,                    # e.g. "50-200 employees"
     "pain_points": list[str],               # 2-4 items
     "recent_news": list[str],               # bullet points, max 3
     "tech_stack": list[str],
     "research_summary": str                 # 2-3 sentences, will be used to open the email
   }
   Prompt is loaded from /agents/prompts/research_prompts.py:
     SYNTHESIS_SYSTEM: "You are a B2B sales researcher. Extract precise, factual information about the company from the provided text. Never invent facts. If you don't know something, omit it."
     Build a user message that includes: website text snippet, news results, tech stack hints.

5. check_quality(state):
   Call gpt-4o-mini with this check:
     "Does this research_summary contain at least one specific, verifiable fact about the company?
      Answer with JSON: { 'passes': bool, 'reason': str }"
   Use OpenAI response_format=json_object.
   If summary word count < 20 → automatic fail (don't call the LLM).
   Return: quality_ok = True/False.

### Edges
START → fetch_website → search_news → extract_tech_stack → synthesize → check_quality
check_quality → END (if quality_ok or refine_count >= 2)
check_quality → synthesize (if not quality_ok, increment refine_count)

### Backend interface: /backend/agents_interface/research.py
async def trigger_research(lead_id: UUID, db: AsyncSession) -> dict:
    1. Load the Lead row.
    2. Call run_research_agent({"company_name": lead.company_name, "website": lead.website})
    3. Save result to lead.research_data (JSON column).
    4. Call vector_store.upsert_company_research(lead_id, result["research_summary"], result)
    5. Update lead.status = "researched".
    6. Return result dict.

### Update /api/internal routes (Phase 2A stubs)
In /backend/api/internal.py, POST /api/internal/trigger-research:
  Now actually calls agents_interface.research.trigger_research(lead_id, db).

### Tests: /backend/tests/test_research_agent.py
Use respx to mock httpx (website fetch), Tavily (news), and both LLM APIs.
  test_happy_path: provide a mock website + news → assert output schema valid
  test_website_unreachable: mock httpx 500 → assert agent still returns (graceful degradation)
  test_quality_check_loop: make first synthesis produce a short summary → assert refine_count incremented
  test_max_retries: make quality always fail → assert AgentOutputError after 2 refines
  test_backend_interface: mock run_research_agent, assert lead.research_data updated in DB

## Constraints
- Do NOT hallucinate company facts — the synthesize prompt must say "never invent".
- Do NOT retry the entire graph on a bad LLM response — only loop the synthesize→check_quality edge.
- Raw website text must be capped at 3000 chars to stay within context limits.
- research_summary must be written in third person ("ABC Corp is..."), not "the company is...".

## Verify
Run: pytest backend/tests/test_research_agent.py -v
Expected: 5 tests pass.

Run: python agents/scripts/smoke.py research
(You'll need to create this script — it calls run_research_agent with company_name="Stripe", website="https://stripe.com" using live APIs. Print the output.)
Expected: structured JSON with non-empty pain_points and research_summary.
```

---

## Phase 3B — Personalization Agent (with Compliance)

### Prompt

```
[Paste the shared context above first]

## Task: Personalization Agent
Location: /agents/personalization_agent.py
Prompts: /agents/prompts/personalization_prompts.py
Entry point:
  async def run_personalization_agent(
      lead: dict,
      research: dict,
      campaign_context: dict,
  ) -> dict

campaign_context shape: { product: str, value_prop: str, case_study: str, tone: str }

### LangGraph state: PersonalizationState (TypedDict)
  lead: dict
  research: dict
  campaign_context: dict
  templates: list[dict]
  draft: dict | None
  compliance_violations: list[str]
  refine_count: int

### Graph nodes

1. retrieve_templates(state):
   Call vector_store.get_best_templates(
       industry=research["industry"],
       pain_point=research["pain_points"][0] if pain_points else ""
   )
   Store in state["templates"].
   If Qdrant unavailable: set templates = [] and continue (graceful degradation).

2. draft_email(state):
   Call Claude claude-sonnet-4-20250514 using tool_use structured output.
   System prompt (from personalization_prompts.py DRAFT_SYSTEM):
     "You write B2B cold emails. You are direct, specific, and never generic.
      Every email must reference one specific fact from the research provided.
      Maximum 150 words in the body. No exclamation marks. No buzzwords.
      Write in a professional but conversational tone."
   
   User message includes:
     - Lead: name, company, any relevant research fields
     - Research summary + top 2 pain points
     - Campaign context (product, value_prop, case_study)
     - 1-2 example templates from retrieved_templates (as few-shot examples, if available)
   
   Output tool schema:
   {
     "subject": str,           # max 60 chars
     "opening_line": str,      # MUST contain a phrase also present in research_summary
     "body": str,              # 100-150 words
     "cta": str,               # one short sentence — no links, no hard sells
     "full_email": str         # subject \n\n opening_line \n\n body \n\n cta
   }

3. compliance_check(state):
   Call gpt-4o-mini (response_format=json_object) with this prompt:
     Check the email for:
     a) Spam trigger words: guaranteed, free money, act now, limited time, click here, 100%,
        unlimited, best price, risk-free, winner, congratulations
     b) Unverifiable claims (ROI percentages, specific revenue figures without attribution)
     c) Body word count > 200
     d) Does opening_line contain text that also appears in the research_summary? (must = yes)
     e) Subject > 60 chars
     
     Return: { "passes": bool, "violations": list[str] }
   
   Store violations in state.
   If passes → proceed to END.
   If fails → add violations as context for refine node.

4. refine(state):
   Call Claude claude-sonnet-4-20250514 again, this time with:
     - Original draft
     - The list of compliance violations as explicit instructions to fix
   Same output schema as draft_email.
   Increment refine_count.
   → Goes back to compliance_check.
   Max refine_count = 2. If still failing after 2 → raise AgentOutputError with violations list.

### Edges
START → retrieve_templates → draft_email → compliance_check
compliance_check → END (passes or refine_count >= 2)
compliance_check → refine (fails and refine_count < 2)
refine → compliance_check

### Backend interface: /backend/agents_interface/personalization.py
async def trigger_personalization(lead_id: UUID, db: AsyncSession) -> dict:
    1. Load Lead + campaign (via campaign_id FK) + existing research_data.
    2. If research_data is None: raise ValueError("Lead must be researched first").
    3. Build campaign_context from campaign.settings.
    4. Call run_personalization_agent(lead, research_data, campaign_context).
    5. Insert into emails table: subject, body (full_email), type="outreach", lead_id.
    6. Return the email dict.

### Tests: /backend/tests/test_personalization_agent.py
  test_happy_path: mock all LLMs → assert email has subject, body, opening_line, cta
  test_compliance_catches_spam: force draft to include "guaranteed" → assert refine triggered
  test_opening_line_must_match_research: force opening_line with no research overlap → assert violation
  test_max_refines_raises: make compliance always fail → assert AgentOutputError
  test_word_count_enforced: force body > 200 words → assert compliance violation "body too long"
  test_no_templates_ok: empty Qdrant response → assert agent still generates valid email

## Constraints
- The opening_line MUST reference text from research_summary. The compliance check enforces this.
- Do NOT strip the compliance check to speed up tests — it is production behavior.
- The system prompt must be loaded from the prompts file, not inlined in the node function.

## Verify
Run: pytest backend/tests/test_personalization_agent.py -v
Expected: 6 tests pass.
```

---

## Phase 3C — Reply Classifier

### Prompt

```
[Paste the shared context above first]

## Task: Reply Classifier
Location: /agents/reply_classifier.py
Prompts: /agents/prompts/classifier_prompts.py
Entry point:
  async def run_reply_classifier(
      reply_text: str,
      prior_email: str | None = None,
  ) -> dict

This agent is a single LLM call (no graph needed — just a structured output call).

### Output schema (Pydantic model: ClassificationResult)
  intent: Literal["interested", "not_interested", "meeting_request",
                   "unsubscribe", "needs_more_info", "unknown"]
  confidence: float  # 0.0-1.0
  suggested_next_action: Literal["schedule_call", "send_followup", "close_lead",
                                   "unsubscribe_lead", "reply_with_info", "wait"]
  key_phrases: list[str]  # phrases from the reply that drove the classification

Intent → suggested_next_action mapping (enforced in Pydantic validator):
  interested → schedule_call
  not_interested → close_lead
  meeting_request → schedule_call
  unsubscribe → unsubscribe_lead
  needs_more_info → reply_with_info
  unknown → wait

Use gpt-4o-mini with OpenAI response_format=json_object.
System prompt (from classifier_prompts.py CLASSIFY_SYSTEM):
  "You classify sales email replies. Return only the JSON structure. Be conservative:
   if the intent is ambiguous, use 'unknown'. 'interested' requires clear positive signal.
   'unsubscribe' requires explicit opt-out language."

### Backend interface: /backend/agents_interface/classifier.py
async def classify_reply(reply_id: UUID, db: AsyncSession) -> ClassificationResult:
    1. Load Reply row.
    2. Load the parent Email row for context.
    3. Call run_reply_classifier(reply.content, prior_email=email.body).
    4. Update reply.classified_as = result.intent.
    5. If intent in ["interested", "meeting_request"]: update lead.status = "meeting_booked".
    6. If intent == "unsubscribe": update lead.status = "unsubscribed".
    7. Return result.

### Update webhook
In /backend/api/webhooks.py, POST /api/webhooks/n8n/reply-received:
  Replace the stub with a real call to classify_reply(reply.id, db).
  Return classified_as from the result.

### Tests: /backend/tests/test_reply_classifier.py
  test_interested_signal: reply = "Sounds great, let's talk next week" → intent: interested
  test_unsubscribe: reply = "Please remove me from your list" → intent: unsubscribe
  test_not_interested: reply = "Not relevant for us right now" → intent: not_interested
  test_ambiguous_unknown: reply = "OK" → intent: unknown
  test_lead_status_updated_on_interest: mock classify to return interested → assert lead.status = meeting_booked
  
All 5 tests mock the OpenAI API with respx.

## Verify
Run: pytest backend/tests/test_reply_classifier.py -v
Expected: 5 tests pass.
```

---

## Phase 3D — Follow-up Agent

### Prompt

```
[Paste the shared context above first]

## Task: Follow-up Agent
Location: /agents/followup_agent.py
Prompts: /agents/prompts/followup_prompts.py
Entry point:
  async def run_followup_agent(
      lead_id: str,
      days_since_last_touch: int,
      original_email: dict,          # { subject, body }
      prior_followups: list[dict],   # list of { type, body } — already sent follow-ups
      research: dict,                # company research from Phase 3A
  ) -> dict

### Output schema (Pydantic model: FollowupResult)
  should_send: bool
  subject: str | None
  body: str | None
  strategy: Literal["day_3_bump", "day_7_value_add", "day_14_breakup", "stop"] | None

### Logic (as a LangGraph conditional graph)

Node: select_strategy(state):
  days = state["days_since_last_touch"]
  if days > 14: return {"strategy": "stop", "should_send": False}
  elif days >= 14: strategy = "day_14_breakup"
  elif days >= 7: strategy = "day_7_value_add"
  else: strategy = "day_3_bump"
  return {"strategy": strategy}

Conditional edge: if strategy == "stop" → END (return should_send: false)
Otherwise → generate_followup

Node: generate_followup(state):
  Call Claude claude-sonnet-4-20250514 with tool_use structured output.
  
  Strategy-specific prompts (from followup_prompts.py):
  
  DAY_3_BUMP_SYSTEM:
    "Write a 2-sentence follow-up bump. Reference the original email's subject.
     Be light, not pushy. Maximum 40 words."
  
  DAY_7_VALUE_ADD_SYSTEM:
    "Write a follow-up that adds value. Share ONE relevant insight about the
     recipient's industry based on their pain points. Maximum 80 words.
     Do not repeat the original pitch."
  
  DAY_14_BREAKUP_SYSTEM:
    "Write a respectful break-up email. Ask if you should close the file.
     Maximum 30 words. Make it easy for them to say no — that's okay."
  
  Check prior_followups: if the same strategy was already used → 
    adjust angle slightly (mention this in the system prompt).
  
  Output tool schema:
  {
    "subject": str,   # for bumps: "Re: [original subject]"
    "body": str
  }

Edges: select_strategy → generate_followup → END
                        → END (if stop)

### Backend interface: /backend/agents_interface/followup.py
async def trigger_followup(lead_id: UUID, db: AsyncSession) -> FollowupResult:
    1. Load Lead, its campaign, and all emails (ordered by sent_at).
    2. Find the most recent email's sent_at. Compute days since sent.
    3. Load all prior follow-up emails for this lead.
    4. Call run_followup_agent(str(lead_id), days, original_email, prior_followups, research).
    5. If result.should_send:
       Insert email row with type="followup".
    6. Return result.

### Tests: /backend/tests/test_followup_agent.py
  test_day_3_bump: days=3 → strategy day_3_bump, should_send: true, body ≤ 40 words
  test_day_7_value_add: days=7 → strategy day_7_value_add
  test_day_14_breakup: days=14 → strategy day_14_breakup, body ≤ 30 words
  test_stop_after_14: days=15 → should_send: false
  test_avoids_repeating_strategy: prior_followups includes a day_3_bump →
    mock LLM called with "adjust angle" in the prompt

## Constraints
- Follow-up emails must NOT repeat the same angle as a prior_followup.
- The breakup email must be genuinely short (≤ 30 words) — test this.
- Do NOT use the same system prompt for all strategies — they are meaningfully different.

## Verify
Run: pytest backend/tests/test_followup_agent.py -v
Expected: 5 tests pass.

Run: python agents/scripts/smoke.py followup
Expected: 4 outputs printed (day 3, 7, 14, and stop) with correct word counts.

Finally: pytest backend/tests/ -v
Expected: All tests across all phases still pass (no regressions).
```

---

## After Phase 3
1. Run `pytest backend/tests/ -v` — all 20+ tests must pass.
2. Run `python agents/scripts/smoke.py all` (you may need to create a top-level smoke runner).
3. Update CLAUDE.md: Phase 3 → ✅ complete.
4. Note in `scratchpad.md`: which model calls cost the most, which prompt refinements were needed.
5. Commit. Open Phase 4 in a new session.
