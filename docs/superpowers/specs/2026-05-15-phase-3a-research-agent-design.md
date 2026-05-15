# Phase 3A — Research Agent Design

> Status: approved (brainstorm 2026-05-15) — ready for implementation plan.
> Source of truth for scope, contracts, and decisions. Supersedes `docs/prompts/phase-3-agents.md` only for Phase 3A.

## 1. Goal

Build `run_research_agent(lead) -> dict`: a LangGraph workflow that fetches a company's website text, retrieves company news via Tavily, synthesizes a structured research dict using Claude, validates quality with GPT-4o-mini, refines up to 2 times, and returns a Pydantic-validated dict consumed by the Personalization Agent, the Qdrant vector store, and the frontend lead drawer.

End-to-end deliverable: agent + prompts + backend interface + internal API route + 5 passing tests + smoke script.

## 2. Prerequisites (must land before agent code)

### 2.1 Make `agents/` an installable package

Reason: `agents/` is a sibling of `backend/`. Imports must resolve in tests (pytest), the API server (uvicorn), CLI smoke scripts, and Docker. The standard Python monorepo pattern fits — package + path dep — and preserves the plane separation described in [agents/README.md](../../../agents/README.md).

- Create `agents/pyproject.toml` with:
  - `name = "sales-automation-agents"`, packages = `["agents"]`
  - Deps: `langgraph>=1.0,<2.0`, `langchain-anthropic`, `langchain-openai`, `anthropic`, `openai`, `tavily-python`, `beautifulsoup4`, `httpx`, `tenacity`, `pydantic>=2`
- Add to `backend/pyproject.toml`: `sales-automation-agents` as a path dep (`pip install -e ../agents` in the backend venv setup).
- Imports become `from agents.research_agent import run_research_agent`.

### 2.2 Settings

Add to `backend/core/config.py`:
- `tavily_api_key: str`
- `openai_api_key: str`
- `anthropic_api_key: str`
- `internal_api_token: str` (new — for the internal API route auth header)

`firecrawl_api_key` stays in `.env.example` for future, but Phase 3A does **not** use Firecrawl (decided: httpx + BeautifulSoup).

Add to `.env.example`: `INTERNAL_API_TOKEN=`.

### 2.3 `AgentOutputError`

Append to [backend/core/exceptions.py](../../../backend/core/exceptions.py):

```python
class AgentOutputError(Exception):
    def __init__(self, agent: str, violations: list[str]):
        self.agent = agent
        self.violations = violations
        super().__init__(f"{agent} failed: {violations}")
```

Register a handler in `register_exception_handlers` that returns status 422 with envelope:

```json
{
  "data": null,
  "error": {"code": "AGENT_OUTPUT_ERROR", "message": "...", "details": {"agent": "...", "violations": [...]}},
  "meta": {}
}
```

### 2.4 Skeleton files

- `agents/prompts/__init__.py` (empty)
- `agents/prompts/research_prompts.py` — `SYNTHESIS_SYSTEM` and `QUALITY_CHECK_SYSTEM` constants
- `agents/scripts/__init__.py` (empty)
- `agents/scripts/smoke.py` — argparse CLI, `research` subcommand
- `backend/api/internal.py` — new router file
- `backend/agents_interface/research.py` — `trigger_research(lead_id, db)`

## 3. Module structure & contracts

### 3.1 `agents/research_agent.py`

Public:
```python
async def run_research_agent(lead: dict) -> dict:
    """lead = {"company_name": str, "website": str}
    Returns dict validated against ResearchOutput.
    Raises AgentOutputError after 2 failed quality refinements
      or on Pydantic validation failure of the final synthesis.
    Never raises on transient network errors — graceful degradation."""
```

Internal:
- `ResearchState(TypedDict)`: `lead`, `raw_website_text`, `news_results`, `tech_stack_hints`, `synthesized`, `quality_ok`, `refine_count`
- `ResearchOutput(BaseModel)`: Pydantic model with `industry: str`, `company_size: str`, `pain_points: list[str]` (length 2–4), `recent_news: list[str]` (max 3), `tech_stack: list[str]`, `research_summary: str`
- 5 node functions: `fetch_website`, `search_news`, `extract_tech_stack`, `synthesize`, `check_quality`
- 1 routing function: `_route_after_quality(state) -> "end" | "synthesize"`
- `_build_graph()` returns compiled graph
- Module-level `_graph = _build_graph()` — compile once at import time
- `run_research_agent` builds initial state, invokes `_graph.ainvoke`, validates with `ResearchOutput`, returns dict

### 3.2 `agents/prompts/research_prompts.py`

Constants only. `SYNTHESIS_SYSTEM` is load-bearing — must specify:
- Output in **third person** ("ABC Corp is...", never "the company is...")
- "Never invent facts not present in the source material"
- If a field is unknown, return a conservative placeholder (e.g. `industry: "Unknown"`)
- `pain_points` and `recent_news` must be grounded in either `raw_website_text` or `news_results`

`QUALITY_CHECK_SYSTEM`: instructs GPT-4o-mini to return `{"passes": bool, "reason": str}` based on whether `research_summary` contains at least one specific, verifiable fact.

### 3.3 `backend/agents_interface/research.py`

```python
async def trigger_research(lead_id: UUID, db: AsyncSession) -> dict:
    lead = await db.get(Lead, lead_id)
    if lead is None:
        raise LookupError(f"Lead {lead_id} not found")

    result = await run_research_agent({
        "company_name": lead.company_name,
        "website": lead.website,
    })

    lead.research_data = result
    lead.status = LeadStatus.RESEARCHED
    await db.commit()

    # Vector upsert is best-effort — DB write is the source of truth.
    # Deviation from prompt spec: spec orders vector before commit;
    # we commit first so agent work survives Qdrant outages.
    try:
        vs = get_vector_store()
        await vs.upsert_company_research(lead_id, result["research_summary"], result)
    except Exception as e:
        logger.warning("Vector upsert failed for lead %s: %s", lead_id, e)

    return result
```

### 3.4 `backend/api/internal.py`

```python
router = APIRouter(prefix="/api/internal", tags=["internal"])

class TriggerResearchBody(BaseModel):
    lead_id: UUID

async def _require_internal_token(x_internal_token: str = Header(...)) -> None:
    if x_internal_token != settings.internal_api_token:
        raise HTTPException(status_code=403, detail="Invalid internal token")

@router.post("/trigger-research", dependencies=[Depends(_require_internal_token)])
async def trigger_research_endpoint(
    body: TriggerResearchBody,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await trigger_research(body.lead_id, db)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"data": result, "error": None, "meta": {}}
```

Wired in `main.py`: `app.include_router(internal.router)`.

### 3.5 `agents/scripts/smoke.py`

```python
# Usage: python agents/scripts/smoke.py research
# Real LLM + real Tavily call against a fixed fixture lead.
# Loads .env, calls run_research_agent, pretty-prints result.
# Exits 1 if pain_points or research_summary are empty.
```

Uses `argparse` with subcommands so future phases (`personalization`, `followup`) can extend.

## 4. Node implementations

### 4.1 `fetch_website` — graceful degradation

```python
async def fetch_website(state: ResearchState) -> dict:
    url = state["lead"]["website"]
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "SalesAutomationBot/1.0"})
            resp.raise_for_status()
        text = await asyncio.to_thread(_extract_text, resp.text)
        return {"raw_website_text": text[:3000]}
    except Exception as e:
        logger.warning("fetch_website failed for %s: %s", url, e)
        return {"raw_website_text": ""}
```

`_extract_text` pulls `<p>`, `<h1>`–`<h3>`, `<meta name=description>`, joins with newlines.

### 4.2 `search_news` — async Tavily

```python
async def search_news(state: ResearchState) -> dict:
    client = AsyncTavilyClient(api_key=settings.tavily_api_key)
    try:
        results = await client.search(
            f"{state['lead']['company_name']} company news 2024 2025",
            max_results=5,
        )
        return {"news_results": results.get("results", [])}
    except Exception as e:
        logger.warning("Tavily search failed: %s", e)
        return {"news_results": []}
```

### 4.3 `extract_tech_stack` — pure Python

Case-insensitive substring scan of `raw_website_text` + concatenated news snippets against the fixed list: Salesforce, HubSpot, Outreach, Gong, Slack, Notion, Jira, AWS, GCP, Azure. Returns dedup'd list.

### 4.4 `synthesize` — Claude tool_use, retry on transient errors only

```python
@retry(
    retry=retry_if_exception_type((
        anthropic.APIConnectionError,
        anthropic.RateLimitError,
        anthropic.APITimeoutError,
    )),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
async def _call_claude_synthesize(messages, refine_context: dict | None) -> dict: ...

async def synthesize(state: ResearchState) -> dict:
    # Increment refine_count when re-entering after a failed quality check.
    # Owning the increment here (not in check_quality) makes the budget
    # arithmetic match `test_max_retries`: 1 initial call + 2 refines = 3 total.
    refine_count = state["refine_count"]
    refine_context = None
    if not state["quality_ok"] and state["synthesized"] is not None:
        refine_count += 1
        refine_context = {
            "prior_summary": state["synthesized"]["research_summary"],
            "instruction": "Previous attempt failed quality check. Write a more specific summary that references a concrete fact from the source material.",
        }
    raw_output = await _call_claude_synthesize(_build_messages(state), refine_context)
    return {"synthesized": raw_output, "refine_count": refine_count}
```

Tool-use call: `client.messages.create(model="claude-sonnet-4-20250514", tools=[{"name": "submit_research", "input_schema": <json schema for ResearchOutput>}], tool_choice={"type": "tool", "name": "submit_research"}, ...)`. Helper: `next(b for b in resp.content if b.type == "tool_use").input`.

**Pydantic validation is deferred to the entry point** — running validation inside the loop would conflate "bad schema" (should raise) with "bad quality" (should refine).

### 4.5 `check_quality` — deterministic + LLM

```python
async def check_quality(state: ResearchState) -> dict:
    summary = state["synthesized"].get("research_summary", "")
    # Deterministic auto-fail: skip the LLM call when the summary is too short.
    if len(summary.split()) < 20:
        return {"quality_ok": False}

    result = await _call_openai_quality(summary)  # {"passes": bool, "reason": str}
    return {"quality_ok": bool(result["passes"])}
```

`refine_count` is incremented inside `synthesize` on re-entry, not here — see section 4.4.

`_call_openai_quality` uses GPT-4o-mini with `response_format={"type": "json_object"}`. Same tenacity decorator pattern as `synthesize`.

### 4.6 Conditional edge

```python
def _route_after_quality(state: ResearchState) -> str:
    if state["quality_ok"] or state["refine_count"] >= 2:
        return "end"
    return "synthesize"

graph.add_conditional_edges(
    "check_quality",
    _route_after_quality,
    {"end": END, "synthesize": "synthesize"},
)
```

### 4.7 Graph wiring

```python
graph = StateGraph(ResearchState)
graph.add_node("fetch_website", fetch_website)
graph.add_node("search_news", search_news)
graph.add_node("extract_tech_stack", extract_tech_stack)
graph.add_node("synthesize", synthesize)
graph.add_node("check_quality", check_quality)

graph.add_edge(START, "fetch_website")
graph.add_edge("fetch_website", "search_news")
graph.add_edge("search_news", "extract_tech_stack")
graph.add_edge("extract_tech_stack", "synthesize")
graph.add_edge("synthesize", "check_quality")
graph.add_conditional_edges("check_quality", _route_after_quality, {"end": END, "synthesize": "synthesize"})

_graph = graph.compile()
```

### 4.8 Entry point — final validation gate

```python
async def run_research_agent(lead: dict) -> dict:
    initial = ResearchState(
        lead=lead, raw_website_text=None, news_results=[],
        tech_stack_hints=[], synthesized=None, quality_ok=False, refine_count=0,
    )
    final = await _graph.ainvoke(initial)

    if not final["quality_ok"]:
        raise AgentOutputError(
            agent="research",
            violations=["quality_check_failed_after_2_refines"],
        )

    try:
        validated = ResearchOutput(**final["synthesized"])
    except ValidationError as e:
        raise AgentOutputError(agent="research", violations=[str(e)])

    return validated.model_dump()
```

## 5. Tests

File: `backend/tests/test_research_agent.py`. 5 tests, all async, all mocked. Implementation follows TDD (Red→Green per node), so tests are written progressively, not as a batch.

### 5.1 Mocking strategy

| Layer | Tool | Rationale |
|---|---|---|
| Website HTTP | `respx` | `httpx.AsyncClient` mocks cleanly |
| Tavily | `unittest.mock.patch` on `AsyncTavilyClient.search` | SDK version variance; patching the method is more stable than HTTP-layer mocks |
| Anthropic | `respx` on `api.anthropic.com/v1/messages` | SDK uses httpx |
| OpenAI | `respx` on `api.openai.com/v1/chat/completions` | SDK uses httpx |

**Fallback plan:** if respx misses Anthropic/OpenAI calls due to transport pinning, switch to `unittest.mock.patch` on the client method. Document in `scratchpad.md`.

### 5.2 Test cases

1. **`test_happy_path`** — mock website 200 with sample HTML; patch Tavily to return 5 results; mock Claude to return a valid tool-use response; mock OpenAI quality check to return `{"passes": true}`. Assert returned dict matches `ResearchOutput`, `pain_points` length 2–4, `research_summary` ≥ 20 words.

2. **`test_website_unreachable`** — mock website 500; LLMs mocked normally. Assert agent completes, returned dict valid, `raw_website_text` was `""` (inspect the Claude call payload via respx).

3. **`test_quality_check_loop`** — Claude returns short summary on first call, valid on second; OpenAI fails quality first, passes second. Assert final `refine_count == 1`, Claude called twice.

4. **`test_max_retries`** — Claude always returns short summary, OpenAI always fails. Assert `AgentOutputError` raised with violations containing `"quality_check_failed_after_2_refines"`; Claude called exactly 3 times (initial + 2 refines).

5. **`test_backend_interface`** — patch `run_research_agent` to return a canned dict; insert a Lead row via factory; call `trigger_research`. Assert `lead.research_data` populated, `lead.status == "researched"`, `vector_store.upsert_company_research` called once with the right args.

## 6. Verification commands

```bash
# Lint
cd backend && .venv/bin/ruff check .

# Required tests
.venv/bin/pytest backend/tests/test_research_agent.py -v
# Expected: 5 passed

# Regression — Phase 1 + 2 tests still pass
.venv/bin/pytest backend/tests/ -v

# Smoke (real APIs, ~$0.02)
python agents/scripts/smoke.py research
# Expected: JSON with non-empty pain_points and research_summary
```

## 7. Risks

1. **respx vs Anthropic/OpenAI httpx transports.** SDKs sometimes pin httpx transports that bypass respx routing. Mitigation: validate on the happy-path test first; fall back to method-level `patch`. Document in `scratchpad.md`.

2. **LangGraph 1.0 `ainvoke` return shape.** Confirm via docs that `ainvoke` returns the merged final state dict (it does in current versions). If wrapped, adjust entry point access.

3. **Claude tool-use response parsing.** Response `content` is a list of blocks; find the `tool_use` block: `next(b for b in resp.content if b.type == "tool_use").input`. If shape changes, isolate parsing in one helper.

4. **`asyncio.to_thread(BeautifulSoup)`.** If pytest-asyncio interacts poorly, fall back to running BS4 inline — HTML is small (≤ 3000 chars after trim), so blocking risk is minimal.

5. **Tavily free tier (1000/month).** Smoke script counts against this. Acceptable for MVP.

6. **Refine doesn't always improve quality.** If the LLM keeps producing low-quality output, both refines fail and we raise. Acceptable — preferable to silent low-quality output.

## 8. Out of scope (Phase 3A only)

- Phases 3B / 3C / 3D agents (separate sessions per the prompt doc)
- Caching research results to short-circuit re-runs
- Multi-language site handling
- Pagination of news results beyond top 5
- Frontend integration (Phase 5)
- n8n workflow that triggers this route (Phase 4)
- Rate-limit handling beyond tenacity backoff
- Firecrawl integration (httpx + BeautifulSoup chosen; key stays in `.env.example` for future)

## 9. Deliverable file checklist

**New files:**
- `agents/pyproject.toml`
- `agents/prompts/__init__.py`
- `agents/prompts/research_prompts.py`
- `agents/scripts/__init__.py`
- `agents/scripts/smoke.py`
- `backend/api/internal.py`
- `backend/tests/test_research_agent.py`

**Modified files:**
- `agents/research_agent.py` — replace stub with full implementation
- `backend/pyproject.toml` — add `sales-automation-agents` path dep
- `backend/core/config.py` — add `tavily_api_key`, `openai_api_key`, `anthropic_api_key`, `internal_api_token`
- `backend/core/exceptions.py` — add `AgentOutputError` + handler
- `backend/main.py` — `include_router(internal.router)`
- `backend/agents_interface/research.py` — replace stub with `trigger_research`
- `.env.example` — add `INTERNAL_API_TOKEN`
- `CLAUDE.md` — mark Phase 3A complete (after verification passes)
- `scratchpad.md` — append Phase 3A notes during/after implementation

## 10. Decisions log (deviations from `docs/prompts/phase-3-agents.md`)

| Decision | Rationale |
|---|---|
| `agents/` as installable package (path dep) | Works in all execution contexts; preserves plane separation |
| httpx + BeautifulSoup, not Firecrawl | No paid dep; graceful degradation rule already handles JS-heavy sites |
| Pydantic validation at entry point, not in loop | Avoids conflating schema errors with quality errors |
| DB commit before vector upsert | DB is source of truth; survives Qdrant outages |
| `X-Internal-Token` header auth on internal route | Minimal protection beyond "internal" naming |
| Refine logic branched inside `synthesize` node (not a separate `refine` node) | Keeps graph small; refine context read from `state["refine_count"]` |
| `refine_count` incremented in `synthesize` on re-entry (not in `check_quality`) | Makes budget arithmetic match `test_max_retries` (1 initial + 2 refines = 3 calls); avoids "off-by-one" between increment site and routing threshold |
| LangGraph pinned to `>=1.0,<2.0` | Current stable; matches docs queried during design |
| Tavily mocked via `patch`, not respx | SDK version variance makes method-level patch more stable |
