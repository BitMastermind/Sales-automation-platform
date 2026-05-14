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

Key constraints for ALL agents:
- Every agent lives in `/agents/` and exports a single async entry point.
- The backend calls agents through `/backend/agents_interface/` — never importing from `/agents/` directly.
- Agents return Pydantic-validated dicts. If validation fails twice → raise `AgentOutputError`.
- Prompts live in `/agents/prompts/<agent_name>.py` — never inline in the graph.
- Models: synthesis nodes use `claude-sonnet-4-20250514`. Quality/classification nodes use `gpt-4o-mini`.
- All LLM calls use structured output mode (Anthropic tool-use or OpenAI `response_format`).
- Retry on transient model errors: 3 attempts with exponential backoff.
- Never retry silently on schema validation failure — surface it as `AgentOutputError`.

---

## Phase 3A — Research Agent

---

#### ROLE & PERSONA

You are a senior AI engineer specializing in LangGraph agent design and B2B sales intelligence pipelines. You have built production-grade web scraping, news aggregation, and LLM synthesis workflows. You understand graceful degradation in distributed async systems.

---

#### TASK & OBJECTIVE

Build a `run_research_agent` LangGraph workflow that fetches website text, retrieves company news via Tavily, synthesizes a structured research dict using Claude, validates quality with GPT-4o-mini, and delivers 5 passing tests with mocked external dependencies.

---

#### MY SITUATION

Phase 2 is complete — the FastAPI backend, Postgres schema, and Qdrant vector store are running. The `/api/internal/trigger-research` route exists as a stub in `agents_interface/research.py`. The `httpx`, `tavily-python`, `anthropic`, and `openai` libraries are in `pyproject.toml`. `TAVILY_API_KEY`, `OPENAI_API_KEY`, and `ANTHROPIC_API_KEY` are in settings.

---

#### CONSTRAINTS

- Do **not** raise on website fetch failure — graceful degradation is correct (set `raw_website_text = ""`, log warning).
- Do **not** retry the entire graph on a bad LLM response — only loop the `synthesize → check_quality` edge.
- Raw website text must be **capped at 3000 chars** to stay within context limits.
- `research_summary` must be written in **third person** ("ABC Corp is..."), never "the company is...".
- Do **not** hallucinate company facts — the synthesis prompt must say "never invent".
- Max `refine_count = 2`. After 2 failed quality checks → raise `AgentOutputError`.

---

#### AUDIENCE FOR THE OUTPUT

The research output dict is consumed by: the Personalization Agent (Phase 3B) as few-shot context, the vector store (for semantic search in future runs), and the frontend lead detail drawer. All fields in the output schema must be present and correctly typed.

---

#### PRIOR ATTEMPTS / WHAT FAILED

This is the first implementation. Avoid these patterns:
- Calling Tavily synchronously inside an async graph node — use `await`.
- Raising `AgentOutputError` on a *transient* API error rather than retrying (use exponential backoff for transient, raise only for repeated validation failure).
- Embedding the prompt string directly in the node function — it must come from `research_prompts.py`.
- Using BeautifulSoup blocking I/O inside an async node without `asyncio.to_thread`.

---

#### FORMAT

Deliver files in this order:
1. `/agents/prompts/research_prompts.py` — `SYNTHESIS_SYSTEM` constant
2. `/agents/research_agent.py` — `ResearchState` TypedDict + 5 nodes + graph + entry point
3. `/backend/agents_interface/research.py` — `trigger_research(lead_id, db)` replacing the stub
4. `/backend/api/internal.py` update — wire `trigger-research` to the real interface function
5. `/backend/tests/test_research_agent.py` — 5 tests
6. `/agents/scripts/smoke.py` — research smoke test
7. Verify commands + expected output.

---

#### TONE & EXPERTISE LEVEL

Expert. LangGraph, async Python, and structured LLM output patterns assumed known. No tutorial comments.

---

#### THINKING INSTRUCTION

Before writing the graph edges, think through the `synthesize → check_quality → refine → check_quality` loop and how LangGraph handles conditional cycles. Flag any LangGraph 0.2+ API changes (e.g. `add_conditional_edges` vs `add_edge`) before writing code. State any assumption about the LangGraph version in use.

---

#### DETAILED SPEC

**`ResearchState` (TypedDict):**
```python
lead: dict                    # { company_name, website }
raw_website_text: str | None
news_results: list[dict]      # from Tavily
tech_stack_hints: list[str]
synthesized: dict | None      # LLM output
quality_ok: bool
refine_count: int             # max 2
```

**Nodes:**

`fetch_website(state)` — GET `lead["website"]` with httpx (timeout 10s). Extract text from `<p>`, `<h1>`–`<h3>`, `<meta description>` using BeautifulSoup. Limit to 3000 chars. On any failure: `raw_website_text = ""`, log warning, do NOT raise.

`search_news(state)` — Tavily search: `f"{company_name} company news 2024 2025"`, `max_results=5`. On any failure: `news_results = []`, log warning.

`extract_tech_stack(state)` — Heuristic scan of website text + news for: Salesforce, HubSpot, Outreach, Gong, Slack, Notion, Jira, AWS, GCP, Azure. Return detected list.

`synthesize(state)` — Claude `claude-sonnet-4-20250514` with tool_use. Output tool schema:
```python
{
  "industry": str,
  "company_size": str,
  "pain_points": list[str],   # 2-4 items
  "recent_news": list[str],   # max 3 bullets
  "tech_stack": list[str],
  "research_summary": str     # 2-3 sentences, used as email opening
}
```
System prompt from `research_prompts.py:SYNTHESIS_SYSTEM`.

`check_quality(state)` — GPT-4o-mini `response_format=json_object`: "Does this research_summary contain at least one specific, verifiable fact? Return `{ passes: bool, reason: str }`". Auto-fail (no LLM call) if word count < 20.

**Edges:**
```
START → fetch_website → search_news → extract_tech_stack → synthesize → check_quality
check_quality → END              (if quality_ok or refine_count >= 2)
check_quality → synthesize       (if not quality_ok, increment refine_count)
```

**Backend interface** — `trigger_research(lead_id, db)`:
1. Load Lead row.
2. Call `run_research_agent({ company_name, website })`.
3. Save result to `lead.research_data`.
4. Call `vector_store.upsert_company_research(lead_id, result["research_summary"], result)`.
5. Update `lead.status = "researched"`.
6. Return result dict.

**Tests** — mock httpx, Tavily, and both LLM APIs with respx:
- `test_happy_path`: mock website + news → assert output schema valid.
- `test_website_unreachable`: mock httpx 500 → assert agent still returns (graceful degradation).
- `test_quality_check_loop`: first synthesis returns short summary → assert `refine_count` incremented.
- `test_max_retries`: quality always fails → assert `AgentOutputError` after 2 refines.
- `test_backend_interface`: mock `run_research_agent`, assert `lead.research_data` updated in DB.

**Verify:**
```bash
pytest backend/tests/test_research_agent.py -v
# Expected: 5 passed

python agents/scripts/smoke.py research
# Expected: structured JSON with non-empty pain_points and research_summary
```

---

## Phase 3B — Personalization Agent (with Compliance)

---

#### ROLE & PERSONA

You are a senior AI engineer who has built production email personalization engines for B2B SaaS. You understand cold email best practices, spam filter mechanics, and how to chain LLM quality loops with compliance enforcement in LangGraph.

---

#### TASK & OBJECTIVE

Build a `run_personalization_agent` LangGraph workflow that retrieves email templates from Qdrant, drafts a personalized cold email with Claude, enforces compliance with GPT-4o-mini, and refines up to 2 times — delivering 6 passing tests with all LLM calls mocked.

---

#### MY SITUATION

Phase 3A is complete — `run_research_agent` and the vector store are working. The `VectorStoreClient` singleton is accessible via `get_vector_store()`. The Personalization Agent entry point stub exists at `/agents/personalization_agent.py`. The `/api/internal/trigger-personalization` route is a stub in `agents_interface/personalization.py`.

---

#### CONSTRAINTS

- The `opening_line` **MUST** contain a phrase also present in `research_summary` — the compliance check enforces this (rule d).
- Do **not** strip the compliance check to speed up tests — it is production behavior.
- System prompts must be loaded from `personalization_prompts.py`, not inlined.
- Max `refine_count = 2`. Still failing after 2 → raise `AgentOutputError` with violations list.
- Email body: 100–150 words. Subject: max 60 chars. No exclamation marks. No buzzwords.

---

#### AUDIENCE FOR THE OUTPUT

The draft email dict is consumed by: the FastAPI backend (stored in the `emails` table), the Gmail send node in n8n (reads `full_email`, `subject`, `lead_email`), and the frontend email thread drawer. The output shape is a contract — any field change breaks downstream.

---

#### PRIOR ATTEMPTS / WHAT FAILED

- Do not invent a "fast path" that skips compliance when `refine_count > 0` — the loop must always run.
- Do not let the compliance node call the LLM to check word count — do that with `len(body.split())` before the LLM call.
- Do not use the same system prompt for `draft_email` and `refine` — refine must include the violations list explicitly in the user message.

---

#### FORMAT

Deliver files in this order:
1. `/agents/prompts/personalization_prompts.py` — `DRAFT_SYSTEM` constant
2. `/agents/personalization_agent.py` — `PersonalizationState` + 4 nodes + graph + entry point
3. `/backend/agents_interface/personalization.py` — `trigger_personalization(lead_id, db)`
4. `/backend/api/internal.py` update — wire `trigger-personalization` to real interface
5. `/backend/tests/test_personalization_agent.py` — 6 tests
6. Verify command + expected output.

---

#### TONE & EXPERTISE LEVEL

Expert. LangGraph conditional edges and Claude tool_use patterns assumed known.

---

#### THINKING INSTRUCTION

Before writing the compliance node, enumerate all 5 check rules (spam words, unverifiable claims, word count, opening_line overlap, subject length) and decide which checks need an LLM call vs. a deterministic Python check. Implement deterministic checks locally — save the LLM call only for checks that require semantic understanding.

---

#### DETAILED SPEC

**`PersonalizationState` (TypedDict):**
```python
lead: dict
research: dict
campaign_context: dict          # { product, value_prop, case_study, tone }
templates: list[dict]
draft: dict | None
compliance_violations: list[str]
refine_count: int
```

**Nodes:**

`retrieve_templates(state)` — `vector_store.get_best_templates(industry, pain_point)`. On Qdrant failure: `templates = []`, continue.

`draft_email(state)` — Claude `claude-sonnet-4-20250514` tool_use. Output schema:
```python
{
  "subject": str,          # max 60 chars
  "opening_line": str,     # MUST contain phrase from research_summary
  "body": str,             # 100-150 words
  "cta": str,              # one sentence, no links, no hard sells
  "full_email": str        # subject \n\n opening_line \n\n body \n\n cta
}
```

`compliance_check(state)` — GPT-4o-mini `response_format=json_object`. Check:
- a) Spam trigger words: guaranteed, free money, act now, limited time, click here, 100%, unlimited, best price, risk-free, winner, congratulations
- b) Unverifiable claims (ROI % / revenue figures without attribution)
- c) Body word count > 200 (check deterministically — no LLM)
- d) `opening_line` overlap with `research_summary` (semantic check via LLM)
- e) Subject > 60 chars (check deterministically)

Returns `{ "passes": bool, "violations": list[str] }`.

`refine(state)` — Claude again with original draft + violations as explicit instructions. Same output schema. Increment `refine_count`. → back to `compliance_check`.

**Edges:**
```
START → retrieve_templates → draft_email → compliance_check
compliance_check → END           (passes or refine_count >= 2)
compliance_check → refine        (fails and refine_count < 2)
refine → compliance_check
```

**Backend interface** — `trigger_personalization(lead_id, db)`:
1. Load Lead + campaign + `research_data`.
2. If `research_data is None`: raise `ValueError("Lead must be researched first")`.
3. Build `campaign_context` from `campaign.settings`.
4. Call `run_personalization_agent(lead, research_data, campaign_context)`.
5. Insert Email row: `subject`, `body=full_email`, `type="outreach"`, `lead_id`.
6. Return email dict.

**Tests:**
- `test_happy_path`: mock all LLMs → assert email has subject, body, opening_line, cta.
- `test_compliance_catches_spam`: force draft to include "guaranteed" → assert refine triggered.
- `test_opening_line_must_match_research`: force no research overlap → assert violation logged.
- `test_max_refines_raises`: compliance always fails → assert `AgentOutputError`.
- `test_word_count_enforced`: force body > 200 words → assert compliance violation "body too long".
- `test_no_templates_ok`: empty Qdrant response → assert agent still generates valid email.

**Verify:**
```bash
pytest backend/tests/test_personalization_agent.py -v
# Expected: 6 passed
```

---

## Phase 3C — Reply Classifier

---

#### ROLE & PERSONA

You are a senior NLP engineer with experience building sales intent classifiers. You design conservative classifiers that avoid false positives on "interested" — preferring `unknown` when the signal is ambiguous.

---

#### TASK & OBJECTIVE

Implement `run_reply_classifier` as a single structured GPT-4o-mini call with a Pydantic `ClassificationResult` output, wire it into the `classify_reply` backend interface, update the webhook to call it, and deliver 5 passing tests with mocked OpenAI.

---

#### MY SITUATION

Phases 3A and 3B are complete. The reply-received webhook at `POST /api/webhooks/n8n/reply-received` currently stubs `classified_as="unknown"`. The `Reply` model has a `classified_as` enum column. The `Lead` model has a `status` column. The `agents_interface/classifier.py` stub raises `NotImplementedError`.

---

#### CONSTRAINTS

- Use **GPT-4o-mini** with `response_format=json_object` — not Claude for this node (cost-sensitive, high volume).
- `"interested"` requires **clear positive signal** — ambiguous replies must be `"unknown"`.
- `"unsubscribe"` requires **explicit opt-out language** — do not infer it from negative tone.
- The intent → `suggested_next_action` mapping is enforced by a **Pydantic validator** — do not rely on the LLM to return the right action.
- This agent has **no graph** — it is a single async function wrapping one structured LLM call.

---

#### AUDIENCE FOR THE OUTPUT

`ClassificationResult` is consumed by: the webhook handler (updates `reply.classified_as` and `lead.status`), the frontend reply badge, and future CRM sync logic. The `suggested_next_action` field will drive n8n routing in a later phase.

---

#### PRIOR ATTEMPTS / WHAT FAILED

- Do not over-classify: if the intent is ambiguous, `unknown` is correct and expected.
- Do not let the Pydantic model accept an intent/action pair that doesn't match the mapping — enforce with `@validator`.
- Do not call this agent from a LangGraph graph — it is a direct async function call.

---

#### FORMAT

Deliver files in this order:
1. `/agents/prompts/classifier_prompts.py` — `CLASSIFY_SYSTEM` constant
2. `/agents/reply_classifier.py` — `ClassificationResult` Pydantic model + `run_reply_classifier` function
3. `/backend/agents_interface/classifier.py` — `classify_reply(reply_id, db)` replacing stub
4. `/backend/api/webhooks.py` update — replace stub with real `classify_reply` call
5. `/backend/tests/test_reply_classifier.py` — 5 tests
6. Verify command + expected output.

---

#### TONE & EXPERTISE LEVEL

Expert. Pydantic v2 validators and OpenAI structured output assumed known.

---

#### THINKING INSTRUCTION

Before writing the Pydantic model, define the full intent → action mapping table. Then decide: should the validator raise on an invalid pair, or silently correct it? State the choice and why before writing the validator.

---

#### DETAILED SPEC

**`ClassificationResult` (Pydantic model):**
```python
intent: Literal["interested", "not_interested", "meeting_request",
                 "unsubscribe", "needs_more_info", "unknown"]
confidence: float                     # 0.0–1.0
suggested_next_action: Literal["schedule_call", "send_followup", "close_lead",
                                 "unsubscribe_lead", "reply_with_info", "wait"]
key_phrases: list[str]                # phrases that drove the classification
```

Intent → action mapping (enforced by Pydantic validator):
```
interested        → schedule_call
not_interested    → close_lead
meeting_request   → schedule_call
unsubscribe       → unsubscribe_lead
needs_more_info   → reply_with_info
unknown           → wait
```

**`classify_reply(reply_id, db)`:**
1. Load Reply row.
2. Load parent Email row.
3. Call `run_reply_classifier(reply.content, prior_email=email.body)`.
4. Update `reply.classified_as = result.intent`.
5. If intent in `["interested", "meeting_request"]`: `lead.status = "meeting_booked"`.
6. If intent == `"unsubscribe"`: `lead.status = "unsubscribed"`.
7. Return result.

**Tests** — all 5 mock OpenAI with respx:
- `test_interested_signal`: "Sounds great, let's talk next week" → `intent: interested`.
- `test_unsubscribe`: "Please remove me from your list" → `intent: unsubscribe`.
- `test_not_interested`: "Not relevant for us right now" → `intent: not_interested`.
- `test_ambiguous_unknown`: "OK" → `intent: unknown`.
- `test_lead_status_updated_on_interest`: mock classify → `interested` → assert `lead.status = meeting_booked`.

**Verify:**
```bash
pytest backend/tests/test_reply_classifier.py -v
# Expected: 5 passed
```

---

## Phase 3D — Follow-up Agent

---

#### ROLE & PERSONA

You are a senior AI engineer with experience in multi-touch sales sequence design and conditional LangGraph workflows. You have built agents that select communication strategies based on elapsed time and prior interaction history.

---

#### TASK & OBJECTIVE

Build a `run_followup_agent` LangGraph conditional graph that selects a follow-up strategy based on days elapsed, generates a strategy-appropriate email with Claude, avoids repeating prior follow-up angles, and delivers 5 passing tests plus a smoke script that prints all 4 strategy outputs.

---

#### MY SITUATION

Phases 3A, 3B, and 3C are complete. The `agents_interface/followup.py` stub raises `NotImplementedError`. The `/api/internal/trigger-followup` route exists as a stub. The `emails` table stores prior follow-ups with `type="followup"`. The `leads-needing-followup` endpoint returns `{ lead_id, days_since_sent }`.

---

#### CONSTRAINTS

- Follow-up emails must **not repeat the same angle** as a prior follow-up — check `prior_followups` before generating.
- The breakup email (day 14) must be ≤ **30 words** — enforce this in tests.
- The day-3 bump must be ≤ **40 words**.
- Do **not** use the same system prompt for all strategies — they are meaningfully different (load each from `followup_prompts.py`).
- If `days_since_last_touch > 14`: `should_send = False`, return immediately without calling the LLM.

---

#### AUDIENCE FOR THE OUTPUT

`FollowupResult` is consumed by: the backend interface (inserts a new Email row if `should_send=True`), the n8n followup_scheduler workflow (reads `should_send`, `subject`, `body`, `lead_email`), and the frontend email thread drawer.

---

#### PRIOR ATTEMPTS / WHAT FAILED

- Do not gate the "stop" path behind an LLM call — `days > 14` is a deterministic check.
- Do not return `should_send=False` for `days=14` — 14 is the breakup email, not stop. Stop is `days > 14`.
- Do not load strategy prompts dynamically with `getattr` — use explicit `if/elif` per strategy.

---

#### FORMAT

Deliver files in this order:
1. `/agents/prompts/followup_prompts.py` — `DAY_3_BUMP_SYSTEM`, `DAY_7_VALUE_ADD_SYSTEM`, `DAY_14_BREAKUP_SYSTEM` constants
2. `/agents/followup_agent.py` — `FollowupState`, `FollowupResult`, 2 nodes + conditional graph + entry point
3. `/backend/agents_interface/followup.py` — `trigger_followup(lead_id, db)` replacing stub
4. `/backend/api/internal.py` update — wire `trigger-followup` to real interface
5. `/backend/tests/test_followup_agent.py` — 5 tests
6. `/agents/scripts/smoke.py` — add `followup` smoke section
7. Verify commands + expected output.

---

#### TONE & EXPERTISE LEVEL

Expert. LangGraph conditional edges and Claude tool_use assumed known. Word count validation in tests assumed straightforward.

---

#### THINKING INSTRUCTION

Before writing the graph, define the `select_strategy` node as a pure deterministic function (no LLM). Then define the conditional edge logic: which exit leads to `END` without calling `generate_followup`. Make the boundary between `days=14` (breakup) and `days>14` (stop) explicit before writing code.

---

#### DETAILED SPEC

**`FollowupResult` (Pydantic model):**
```python
should_send: bool
subject: str | None
body: str | None
strategy: Literal["day_3_bump", "day_7_value_add", "day_14_breakup", "stop"] | None
```

**`FollowupState` (TypedDict):**
```python
lead_id: str
days_since_last_touch: int
original_email: dict              # { subject, body }
prior_followups: list[dict]       # [{ type, body }]
research: dict
strategy: str | None
should_send: bool
subject: str | None
body: str | None
```

**Nodes:**

`select_strategy(state)`:
```python
days = state["days_since_last_touch"]
if days > 14:  return { "strategy": "stop", "should_send": False }
elif days >= 14: strategy = "day_14_breakup"
elif days >= 7:  strategy = "day_7_value_add"
else:            strategy = "day_3_bump"
return { "strategy": strategy, "should_send": True }
```

Conditional edge: `"stop"` → END; otherwise → `generate_followup`.

`generate_followup(state)` — Claude `claude-sonnet-4-20250514` tool_use. Load system prompt from `followup_prompts.py` based on `state["strategy"]`. If same strategy already in `prior_followups` → append "Adjust the angle slightly" to the system prompt. Output: `{ "subject": str, "body": str }`.

**Edges:**
```
START → select_strategy
select_strategy → END               (strategy == "stop")
select_strategy → generate_followup (otherwise)
generate_followup → END
```

**Backend interface** — `trigger_followup(lead_id, db)`:
1. Load Lead, campaign, and all emails ordered by `sent_at`.
2. Find most recent email's `sent_at`. Compute days elapsed.
3. Load all prior follow-up emails for this lead.
4. Call `run_followup_agent(str(lead_id), days, original_email, prior_followups, research)`.
5. If `result.should_send`: insert Email row with `type="followup"`.
6. Return result.

**Tests:**
- `test_day_3_bump`: days=3 → strategy `day_3_bump`, `should_send=True`, body ≤ 40 words.
- `test_day_7_value_add`: days=7 → strategy `day_7_value_add`.
- `test_day_14_breakup`: days=14 → strategy `day_14_breakup`, body ≤ 30 words.
- `test_stop_after_14`: days=15 → `should_send=False`.
- `test_avoids_repeating_strategy`: `prior_followups` includes a `day_3_bump` → assert LLM called with "adjust angle" in prompt.

**Verify:**
```bash
pytest backend/tests/test_followup_agent.py -v
# Expected: 5 passed

python agents/scripts/smoke.py followup
# Expected: 4 outputs (day 3, 7, 14, stop) with correct word counts

pytest backend/tests/ -v
# Expected: All tests across all phases still pass (no regressions)
```

---

## After Phase 3

1. Run `pytest backend/tests/ -v` — all 20+ tests must pass.
2. Run `python agents/scripts/smoke.py all`.
3. Update `CLAUDE.md`: Phase 3 → ✅ complete.
4. Note in `scratchpad.md`: which model calls cost the most, which prompt refinements were needed.
5. Commit. Open Phase 4 in a new session.
