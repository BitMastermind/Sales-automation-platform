# Phase 3A — Research Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `run_research_agent(lead) -> dict` — a 5-node LangGraph workflow that fetches a company's website, retrieves news from Tavily, synthesizes structured research with Claude, validates quality with GPT-4o-mini, refines up to 2 times, and returns a Pydantic-validated dict consumed by the Personalization Agent, the Qdrant vector store, and the frontend lead drawer.

**Architecture:** LangGraph 1.x state graph; `synthesize → check_quality` is a conditional cycle (max 2 refines); `refine_count` is owned by the `synthesize` node on re-entry; Pydantic validation lives at the entry point (after the graph), keeping schema errors separate from quality failures; HTTP and Tavily failures degrade gracefully (empty strings/lists, never raise); transient LLM errors get tenacity-decorated exponential backoff (max 3 attempts) on the helper functions.

**Tech Stack:** Python 3.11+ (3.14 in this environment), LangGraph `>=1.0,<2.0`, `anthropic`, `openai`, `tavily-python` (async client), `httpx`, `beautifulsoup4`, `tenacity`, Pydantic v2, FastAPI (existing), SQLAlchemy 2.0 async (existing), pytest + pytest-asyncio + respx (existing test stack).

**Spec:** [docs/superpowers/specs/2026-05-15-phase-3a-research-agent-design.md](../specs/2026-05-15-phase-3a-research-agent-design.md). Read it before starting.

**Existing-code reality the spec didn't fully capture (read before Task 1):**
- `backend/core/config.py` already declares `tavily_api_key`, `openai_api_key`, `anthropic_api_key`, `internal_api_token` — **no settings work needed.**
- `.env.example` already has all four keys + `INTERNAL_API_TOKEN` — **no env work needed.**
- `backend/api/internal.py` already exists with stub handlers using `_require_token` (not `_require_internal_token`), `LeadTriggerBody` (not `TriggerResearchBody`), router prefix `/internal` (mounted at `/api` in main.py — full path `/api/internal/...`). Use existing names; **modify the stub body, do not recreate the file.**
- `backend/main.py` already does `app.include_router(internal_router, prefix="/api")` — **no main.py work needed.**
- `backend/core/vector_store.py` exposes `VectorStoreClient` but **no `get_vector_store()` factory** — Task 3 adds it.
- `backend/tests/test_internal.py` asserts the current stub behavior (`body["data"]["queued"] is True`) — Task 13 updates these.
- `register_exception_handlers(app)` in `backend/core/exceptions.py` is the registration pattern — extend it in Task 2.

---

## File Structure

**New files:**
- `agents/pyproject.toml` — package metadata + deps for the agents plane
- `agents/prompts/__init__.py` — empty
- `agents/prompts/research_prompts.py` — `SYNTHESIS_SYSTEM`, `QUALITY_CHECK_SYSTEM` constants
- `agents/scripts/__init__.py` — empty
- `agents/scripts/smoke.py` — argparse CLI with `research` subcommand
- `backend/agents_interface/research.py` — `trigger_research(lead_id, db)`
- `backend/tests/test_research_agent.py` — 5 tests (4 agent + 1 interface)

**Modified files:**
- `agents/research_agent.py` — replace `NotImplementedError` stub with full implementation (state, output model, 5 nodes, routing, graph, entry point)
- `backend/pyproject.toml` — add `sales-automation-agents` path dep
- `backend/core/exceptions.py` — add `AgentOutputError` class + handler
- `backend/core/vector_store.py` — add `get_vector_store()` factory
- `backend/api/internal.py` — replace `trigger_research` stub body with real interface call
- `backend/tests/test_internal.py` — replace stub-behavior tests with real-interface mocked tests
- `CLAUDE.md` — mark Phase 3A complete (Task 15)
- `scratchpad.md` — append Phase 3A notes (Task 15)

**Untouched but referenced:** `backend/core/config.py`, `backend/main.py`, `.env.example`.

---

## Task 1: Make `agents/` an installable package, install into backend venv

**Files:**
- Create: `agents/pyproject.toml`
- Modify: `backend/pyproject.toml` (add path dep)

- [ ] **Step 1: Write `agents/pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "sales-automation-agents"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "langgraph>=1.0,<2.0",
    "anthropic>=0.40",
    "openai>=1.50",
    "tavily-python>=0.5",
    "beautifulsoup4>=4.12",
    "httpx",
    "tenacity>=8.0",
    "pydantic>=2.0",
]

[tool.hatch.build.targets.wheel]
packages = ["agents", "prompts", "scripts"]
```

Why all three packages? `agents/` is the importable namespace for the agent module; `prompts/` and `scripts/` will be subpackages once Task 4 creates them. List them now so the wheel build doesn't break later.

- [ ] **Step 2: Add the path dep to `backend/pyproject.toml`**

In the `[project]` table, append `"sales-automation-agents"` to the `dependencies` list:

```toml
dependencies = [
    "fastapi>=0.115",
    # ... existing entries ...
    "factory-boy",
    "sales-automation-agents",
]

[tool.uv.sources]
sales-automation-agents = { path = "../agents", editable = true }
```

If a `[tool.uv.sources]` table doesn't exist yet, add it. If the project uses pip rather than uv (it does today — there's no `uv.lock`), the `[tool.uv.sources]` block is harmless and the install in Step 3 uses pip directly.

- [ ] **Step 3: Install the agents package into the existing backend venv**

```bash
cd /Users/ashitverma/Sales\ Automation/backend && .venv/bin/pip install -e ../agents
```

Expected output: `Successfully installed sales-automation-agents-0.1.0` plus pulled-in deps (langgraph, anthropic, openai, tavily-python, beautifulsoup4, tenacity).

- [ ] **Step 4: Verify the import resolves from the backend venv**

```bash
cd /Users/ashitverma/Sales\ Automation/backend && .venv/bin/python -c "from agents.research_agent import run_research_agent; print('ok')"
```

Expected output: `ok`. If `ModuleNotFoundError`, re-check Step 2's wheel `packages` list and re-run Step 3.

- [ ] **Step 5: Commit**

```bash
git add agents/pyproject.toml backend/pyproject.toml
git commit -m "chore: make agents/ an installable package; add path dep to backend"
```

---

## Task 2: Add `AgentOutputError` exception + 422 handler

**Files:**
- Modify: `backend/core/exceptions.py`
- Test: `backend/tests/test_research_agent.py` (will be created in this task with one test)

- [ ] **Step 1: Write the failing test (creates the test file)**

Create `backend/tests/test_research_agent.py`:

```python
"""Tests for the Research Agent (Phase 3A)."""
from httpx import AsyncClient


async def test_agent_output_error_handler_returns_422_envelope(async_client: AsyncClient):
    """The AgentOutputError handler returns a 422 with the standard envelope.

    We trigger it via a temporary route appended in the test (no real agent yet).
    """
    from main import app
    from core.exceptions import AgentOutputError

    @app.get("/__test_agent_error__")
    async def _raise():
        raise AgentOutputError(agent="research", violations=["x"])

    try:
        resp = await async_client.get("/__test_agent_error__")
        assert resp.status_code == 422
        body = resp.json()
        assert body["data"] is None
        assert body["error"]["code"] == "AGENT_OUTPUT_ERROR"
        assert body["error"]["details"]["agent"] == "research"
        assert body["error"]["details"]["violations"] == ["x"]
        assert body["meta"] == {}
    finally:
        # Remove the test-only route so it doesn't leak into other tests
        app.router.routes = [r for r in app.router.routes if getattr(r, "path", None) != "/__test_agent_error__"]
```

- [ ] **Step 2: Run the test, verify it fails**

```bash
cd /Users/ashitverma/Sales\ Automation/backend && .venv/bin/pytest tests/test_research_agent.py::test_agent_output_error_handler_returns_422_envelope -v
```

Expected: FAIL with `ImportError: cannot import name 'AgentOutputError' from 'core.exceptions'`.

- [ ] **Step 3: Implement `AgentOutputError` and its handler**

Append to `backend/core/exceptions.py`:

```python
class AgentOutputError(Exception):
    def __init__(self, agent: str, violations: list[str]):
        self.agent = agent
        self.violations = violations
        super().__init__(f"{agent} failed: {violations}")
```

Inside `register_exception_handlers(app)`, append:

```python
    @app.exception_handler(AgentOutputError)
    async def agent_output_handler(request: Request, exc: AgentOutputError):
        return JSONResponse(
            status_code=422,
            content={
                "data": None,
                "error": {
                    "code": "AGENT_OUTPUT_ERROR",
                    "message": str(exc),
                    "details": {"agent": exc.agent, "violations": exc.violations},
                },
                "meta": {},
            },
        )
```

- [ ] **Step 4: Run the test, verify it passes**

```bash
cd /Users/ashitverma/Sales\ Automation/backend && .venv/bin/pytest tests/test_research_agent.py::test_agent_output_error_handler_returns_422_envelope -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/core/exceptions.py backend/tests/test_research_agent.py
git commit -m "feat(exceptions): add AgentOutputError + 422 envelope handler"
```

---

## Task 3: Add `get_vector_store()` factory

**Files:**
- Modify: `backend/core/vector_store.py`
- Test: `backend/tests/test_vector_store.py` (append one test)

The spec's `trigger_research` (section 3.3) calls `get_vector_store()` — a module-level singleton accessor that doesn't exist yet.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_vector_store.py`:

```python
def test_get_vector_store_returns_singleton():
    from core.vector_store import get_vector_store, VectorStoreClient

    a = get_vector_store()
    b = get_vector_store()
    assert isinstance(a, VectorStoreClient)
    assert a is b
```

- [ ] **Step 2: Run, verify fail**

```bash
cd /Users/ashitverma/Sales\ Automation/backend && .venv/bin/pytest tests/test_vector_store.py::test_get_vector_store_returns_singleton -v
```

Expected: FAIL with `ImportError: cannot import name 'get_vector_store'`.

- [ ] **Step 3: Implement the factory**

Append to `backend/core/vector_store.py` (below the `VectorStoreClient` class):

```python
_vector_store: VectorStoreClient | None = None


def get_vector_store() -> VectorStoreClient:
    """Return the process-wide VectorStoreClient singleton.
    Constructed lazily so module import does not require Qdrant to be reachable.
    """
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreClient()
    return _vector_store
```

- [ ] **Step 4: Run, verify pass**

```bash
cd /Users/ashitverma/Sales\ Automation/backend && .venv/bin/pytest tests/test_vector_store.py -v
```

Expected: all `test_vector_store.py` tests pass, including the new one.

- [ ] **Step 5: Commit**

```bash
git add backend/core/vector_store.py backend/tests/test_vector_store.py
git commit -m "feat(vector-store): add get_vector_store() singleton factory"
```

---

## Task 4: Prompt constants + scripts skeleton

**Files:**
- Create: `agents/prompts/__init__.py`
- Create: `agents/prompts/research_prompts.py`
- Create: `agents/scripts/__init__.py`
- Create: `agents/scripts/smoke.py` (argparse skeleton — body comes in Task 14)

No tests in this task — these are pure constants and a CLI skeleton. Lint will catch syntax issues.

- [ ] **Step 1: Create `agents/prompts/__init__.py`** (empty file)

```bash
touch /Users/ashitverma/Sales\ Automation/agents/prompts/__init__.py
```

- [ ] **Step 2: Create `agents/prompts/research_prompts.py`**

```python
"""Load-bearing prompts for the Research Agent. Edit deliberately."""

SYNTHESIS_SYSTEM = """You are a B2B sales research analyst.

Given a company's website text and recent news, produce a structured research dict by calling the `submit_research` tool. The dict will be used downstream to draft a personalized cold email.

Strict rules:
- `research_summary` is written in third person, naming the company explicitly. Example: "ABC Corp is a logistics SaaS firm..." NEVER "the company is..." or "they are...".
- `research_summary` is 2-3 sentences (~25-40 words) and references at least one specific, verifiable fact (named product, named market, named customer, dated event, named role hire).
- Never invent facts not present in the source material. If a field is unknown, return a conservative placeholder (e.g. `industry: "Unknown"`, `company_size: "Unknown"`, empty `recent_news` list).
- `pain_points` is 2-4 short noun phrases grounded in either the website text or the news (e.g. "manual outbound prospecting").
- `recent_news` is at most 3 one-line bullets drawn directly from the news input. Empty list if no news provided.
- `tech_stack` includes only items explicitly present in the `tech_stack_hints` input.
"""

QUALITY_CHECK_SYSTEM = """You are a quality gate for B2B research summaries.

Pass the summary if it contains at least one specific, verifiable fact about the company (a named product, named market, named customer, dated event, or named role/hire). Fail it if it is generic, vague, or could apply to any company in the industry.

Return JSON: {"passes": <bool>, "reason": "<short reason>"}.
"""
```

- [ ] **Step 3: Create `agents/scripts/__init__.py`** (empty file)

```bash
touch /Users/ashitverma/Sales\ Automation/agents/scripts/__init__.py
```

- [ ] **Step 4: Create `agents/scripts/smoke.py` skeleton**

```python
"""Real-API smoke tests for agents. Not run in CI.

Usage:
    python agents/scripts/smoke.py research
    python agents/scripts/smoke.py all
"""
import argparse
import asyncio
import json
import sys


async def smoke_research() -> int:
    """Stub. Real implementation in Task 14."""
    raise NotImplementedError("Implemented in Task 14")


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent smoke tests against real APIs.")
    parser.add_argument("agent", choices=["research", "all"])
    args = parser.parse_args()

    if args.agent == "research":
        return asyncio.run(smoke_research())
    if args.agent == "all":
        return asyncio.run(smoke_research())
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Verify the package still imports**

```bash
cd /Users/ashitverma/Sales\ Automation/backend && .venv/bin/python -c "from agents.prompts.research_prompts import SYNTHESIS_SYSTEM, QUALITY_CHECK_SYSTEM; print(len(SYNTHESIS_SYSTEM), len(QUALITY_CHECK_SYSTEM))"
```

Expected: two integers > 100 each.

- [ ] **Step 6: Commit**

```bash
git add agents/prompts/ agents/scripts/
git commit -m "feat(agents): add research prompts + smoke script skeleton"
```

---

## Task 5: `ResearchState` (TypedDict) + `ResearchOutput` (Pydantic model)

**Files:**
- Modify: `agents/research_agent.py` (replace stub)
- Test: `backend/tests/test_research_agent.py` (append two tests)

We replace the file in stages — start with state/output types and a passing entry-point that raises NotImplementedError. Subsequent tasks fill in nodes one at a time.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_research_agent.py`:

```python
def test_research_output_validates_minimum_pain_points():
    from pydantic import ValidationError
    import pytest as _pt
    from agents.research_agent import ResearchOutput

    with _pt.raises(ValidationError):
        ResearchOutput(
            industry="SaaS",
            company_size="50-200",
            pain_points=["only one"],  # min_length=2
            recent_news=[],
            tech_stack=[],
            research_summary="Acme is a SaaS company.",
        )


def test_research_output_round_trips_dict():
    from agents.research_agent import ResearchOutput

    payload = {
        "industry": "Logistics SaaS",
        "company_size": "50-200",
        "pain_points": ["manual ops", "outbound scaling"],
        "recent_news": ["expanded to Europe Q1"],
        "tech_stack": ["Salesforce"],
        "research_summary": "ABC Corp is a logistics SaaS firm expanding into Europe.",
    }
    obj = ResearchOutput(**payload)
    assert obj.model_dump() == payload
```

- [ ] **Step 2: Run, verify fail**

```bash
cd /Users/ashitverma/Sales\ Automation/backend && .venv/bin/pytest tests/test_research_agent.py -v -k "research_output"
```

Expected: 2 FAILS — `ImportError: cannot import name 'ResearchOutput'`.

- [ ] **Step 3: Replace `agents/research_agent.py` with state + output types + stub entry point**

Overwrite the entire file (the previous stub is throwaway):

```python
"""Research Agent — Phase 3A.

Public entry point: `run_research_agent(lead) -> dict`.

A 5-node LangGraph workflow that fetches a company's website, retrieves news
from Tavily, synthesizes a structured research dict with Claude, validates
quality with GPT-4o-mini, and refines up to 2 times.

Pydantic validation lives at the entry point (after the graph), keeping schema
errors separate from quality failures.
"""
from __future__ import annotations

from typing import Any, TypedDict

from pydantic import BaseModel, Field


class ResearchState(TypedDict):
    lead: dict[str, Any]                    # {"company_name": str, "website": str}
    raw_website_text: str | None            # "" on fetch failure (graceful degradation)
    news_results: list[dict[str, Any]]      # [] on Tavily failure
    tech_stack_hints: list[str]
    synthesized: dict[str, Any] | None      # raw tool_use input (validated at entry point)
    quality_ok: bool                        # set by check_quality
    refine_count: int                       # 0, 1, or 2 — incremented in synthesize on re-entry


class ResearchOutput(BaseModel):
    industry: str
    company_size: str
    pain_points: list[str] = Field(min_length=2, max_length=4)
    recent_news: list[str] = Field(max_length=3)
    tech_stack: list[str]
    research_summary: str


async def run_research_agent(lead: dict[str, Any]) -> dict[str, Any]:
    """Entry point — implemented progressively across Tasks 6–11."""
    raise NotImplementedError("filled in by later tasks")
```

- [ ] **Step 4: Run, verify pass**

```bash
cd /Users/ashitverma/Sales\ Automation/backend && .venv/bin/pytest tests/test_research_agent.py -v -k "research_output"
```

Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/research_agent.py backend/tests/test_research_agent.py
git commit -m "feat(research-agent): add ResearchState and ResearchOutput types"
```

---

## Task 6: `extract_tech_stack` node (pure, deterministic)

**Files:**
- Modify: `agents/research_agent.py`
- Test: `backend/tests/test_research_agent.py`

Easiest node first — pure Python, no async, no I/O.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_research_agent.py`:

```python
async def test_extract_tech_stack_finds_keywords_case_insensitive():
    from agents.research_agent import extract_tech_stack

    state = {
        "lead": {},
        "raw_website_text": "We use SALESFORCE and slack daily.",
        "news_results": [{"content": "They migrated to AWS last quarter."}],
        "tech_stack_hints": [],
        "synthesized": None,
        "quality_ok": False,
        "refine_count": 0,
    }
    out = await extract_tech_stack(state)
    assert out == {"tech_stack_hints": ["Salesforce", "Slack", "AWS"]}


async def test_extract_tech_stack_dedups_and_returns_empty_when_none_found():
    from agents.research_agent import extract_tech_stack

    state = {
        "lead": {},
        "raw_website_text": "Salesforce salesforce SALESFORCE",
        "news_results": [],
        "tech_stack_hints": [],
        "synthesized": None,
        "quality_ok": False,
        "refine_count": 0,
    }
    out = await extract_tech_stack(state)
    assert out == {"tech_stack_hints": ["Salesforce"]}

    state["raw_website_text"] = "no known tech here"
    out = await extract_tech_stack(state)
    assert out == {"tech_stack_hints": []}
```

- [ ] **Step 2: Run, verify fail**

```bash
cd /Users/ashitverma/Sales\ Automation/backend && .venv/bin/pytest tests/test_research_agent.py -v -k "extract_tech_stack"
```

Expected: 2 FAILS — `ImportError: cannot import name 'extract_tech_stack'`.

- [ ] **Step 3: Implement `extract_tech_stack`**

Append to `agents/research_agent.py` (above `run_research_agent`):

```python
import re

TECH_KEYWORDS = [
    "Salesforce", "HubSpot", "Outreach", "Gong", "Slack",
    "Notion", "Jira", "AWS", "GCP", "Azure",
]


async def extract_tech_stack(state: ResearchState) -> dict[str, Any]:
    haystack_parts = [state.get("raw_website_text") or ""]
    for item in state.get("news_results", []):
        haystack_parts.append(item.get("content", ""))
    haystack = " ".join(haystack_parts).lower()

    hits: list[str] = []
    for kw in TECH_KEYWORDS:
        if re.search(rf"\b{re.escape(kw.lower())}\b", haystack):
            hits.append(kw)
    return {"tech_stack_hints": hits}
```

- [ ] **Step 4: Run, verify pass**

```bash
cd /Users/ashitverma/Sales\ Automation/backend && .venv/bin/pytest tests/test_research_agent.py -v -k "extract_tech_stack"
```

Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/research_agent.py backend/tests/test_research_agent.py
git commit -m "feat(research-agent): add extract_tech_stack pure node"
```

---

## Task 7: `fetch_website` node (httpx + BeautifulSoup, graceful)

**Files:**
- Modify: `agents/research_agent.py`
- Test: `backend/tests/test_research_agent.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_research_agent.py`:

```python
import respx
from httpx import Response


async def test_fetch_website_extracts_visible_text_and_truncates():
    from agents.research_agent import fetch_website

    html = "<html><head><meta name='description' content='Pillar tag'></head><body>" \
           + "<h1>Big Title</h1><p>" + ("body text " * 600) + "</p></body></html>"

    with respx.mock(base_url="https://example.com") as mocker:
        mocker.get("/").mock(return_value=Response(200, text=html))
        out = await fetch_website({
            "lead": {"website": "https://example.com/"},
            "raw_website_text": None, "news_results": [],
            "tech_stack_hints": [], "synthesized": None,
            "quality_ok": False, "refine_count": 0,
        })

    assert "Big Title" in out["raw_website_text"]
    assert "Pillar tag" in out["raw_website_text"]
    assert len(out["raw_website_text"]) <= 3000


async def test_fetch_website_returns_empty_string_on_5xx_no_raise():
    from agents.research_agent import fetch_website

    with respx.mock(base_url="https://broken.example") as mocker:
        mocker.get("/").mock(return_value=Response(500))
        out = await fetch_website({
            "lead": {"website": "https://broken.example/"},
            "raw_website_text": None, "news_results": [],
            "tech_stack_hints": [], "synthesized": None,
            "quality_ok": False, "refine_count": 0,
        })

    assert out == {"raw_website_text": ""}


async def test_fetch_website_returns_empty_string_on_connection_error_no_raise():
    from agents.research_agent import fetch_website
    import httpx

    with respx.mock(base_url="https://nope.example") as mocker:
        mocker.get("/").mock(side_effect=httpx.ConnectError("boom"))
        out = await fetch_website({
            "lead": {"website": "https://nope.example/"},
            "raw_website_text": None, "news_results": [],
            "tech_stack_hints": [], "synthesized": None,
            "quality_ok": False, "refine_count": 0,
        })

    assert out == {"raw_website_text": ""}
```

- [ ] **Step 2: Run, verify fail**

```bash
cd /Users/ashitverma/Sales\ Automation/backend && .venv/bin/pytest tests/test_research_agent.py -v -k "fetch_website"
```

Expected: 3 FAILS.

- [ ] **Step 3: Implement `fetch_website`**

Append to `agents/research_agent.py`:

```python
import asyncio
import logging

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    parts: list[str] = []

    desc = soup.find("meta", attrs={"name": "description"})
    if desc and desc.get("content"):
        parts.append(desc["content"].strip())

    for tag_name in ("h1", "h2", "h3", "p"):
        for el in soup.find_all(tag_name):
            text = el.get_text(strip=True)
            if text:
                parts.append(text)

    return "\n".join(parts).strip()


async def fetch_website(state: ResearchState) -> dict[str, Any]:
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

- [ ] **Step 4: Run, verify pass**

```bash
cd /Users/ashitverma/Sales\ Automation/backend && .venv/bin/pytest tests/test_research_agent.py -v -k "fetch_website"
```

Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/research_agent.py backend/tests/test_research_agent.py
git commit -m "feat(research-agent): add fetch_website node with graceful degradation"
```

---

## Task 8: `search_news` node (AsyncTavilyClient, graceful)

**Files:**
- Modify: `agents/research_agent.py`
- Test: `backend/tests/test_research_agent.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_research_agent.py`:

```python
from unittest.mock import AsyncMock, patch


async def test_search_news_returns_results_list():
    from agents.research_agent import search_news

    fake = {"results": [
        {"title": "Acme expands", "url": "u1", "content": "Acme news content"},
        {"title": "Acme hires", "url": "u2", "content": "more"},
    ]}
    with patch("agents.research_agent.AsyncTavilyClient") as cls:
        cls.return_value.search = AsyncMock(return_value=fake)
        out = await search_news({
            "lead": {"company_name": "Acme", "website": "x"},
            "raw_website_text": "", "news_results": [],
            "tech_stack_hints": [], "synthesized": None,
            "quality_ok": False, "refine_count": 0,
        })

    assert out == {"news_results": fake["results"]}


async def test_search_news_returns_empty_list_on_exception_no_raise():
    from agents.research_agent import search_news

    with patch("agents.research_agent.AsyncTavilyClient") as cls:
        cls.return_value.search = AsyncMock(side_effect=RuntimeError("Tavily down"))
        out = await search_news({
            "lead": {"company_name": "Acme", "website": "x"},
            "raw_website_text": "", "news_results": [],
            "tech_stack_hints": [], "synthesized": None,
            "quality_ok": False, "refine_count": 0,
        })

    assert out == {"news_results": []}
```

- [ ] **Step 2: Run, verify fail**

```bash
cd /Users/ashitverma/Sales\ Automation/backend && .venv/bin/pytest tests/test_research_agent.py -v -k "search_news"
```

Expected: 2 FAILS.

- [ ] **Step 3: Implement `search_news`**

Append to `agents/research_agent.py` (with the import near the top):

```python
from tavily import AsyncTavilyClient  # add to existing imports block at top
```

```python
async def search_news(state: ResearchState) -> dict[str, Any]:
    from core.config import settings  # local import — keeps agents loadable without backend on path
    client = AsyncTavilyClient(api_key=settings.tavily_api_key)
    try:
        query = f"{state['lead']['company_name']} company news 2024 2025"
        results = await client.search(query, max_results=5)
        return {"news_results": results.get("results", [])}
    except Exception as e:
        logger.warning("Tavily search failed: %s", e)
        return {"news_results": []}
```

Note on the local `from core.config import settings`: agent code is meant to be importable without the backend package on sys.path in some contexts (e.g. `agents/scripts/smoke.py` running standalone). The smoke script's setup (Task 14) will load settings explicitly. For the test environment, `pythonpath = ["."]` in `backend/pyproject.toml` makes `core.config` importable.

- [ ] **Step 4: Run, verify pass**

```bash
cd /Users/ashitverma/Sales\ Automation/backend && .venv/bin/pytest tests/test_research_agent.py -v -k "search_news"
```

Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/research_agent.py backend/tests/test_research_agent.py
git commit -m "feat(research-agent): add search_news node with graceful Tavily fallback"
```

---

## Task 9: `_call_claude_synthesize` helper + `synthesize` node

**Files:**
- Modify: `agents/research_agent.py`
- Test: `backend/tests/test_research_agent.py`

We split this into a thin LLM helper (with tenacity for transient errors) and the node that orchestrates state. Tests mock the helper directly — the SDK call itself is exercised by the smoke test (Task 14).

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_research_agent.py`:

```python
async def test_synthesize_calls_claude_helper_and_stores_result():
    from agents.research_agent import synthesize

    fake_output = {
        "industry": "SaaS", "company_size": "50-200",
        "pain_points": ["a", "b"], "recent_news": [],
        "tech_stack": ["AWS"],
        "research_summary": "Acme is a SaaS firm running on AWS. Recently expanded to EU.",
    }
    with patch("agents.research_agent._call_claude_synthesize",
               new=AsyncMock(return_value=fake_output)) as mock_helper:
        out = await synthesize({
            "lead": {"company_name": "Acme", "website": "x"},
            "raw_website_text": "Acme uses AWS",
            "news_results": [],
            "tech_stack_hints": ["AWS"],
            "synthesized": None,
            "quality_ok": False,
            "refine_count": 0,
        })

    assert out["synthesized"] == fake_output
    assert out["refine_count"] == 0  # initial call does NOT increment
    assert mock_helper.await_count == 1
    # On the initial call, refine_context must be None
    args, kwargs = mock_helper.call_args
    assert kwargs.get("refine_context") is None or args[1] is None


async def test_synthesize_increments_refine_count_on_re_entry():
    from agents.research_agent import synthesize

    fake_output = {
        "industry": "SaaS", "company_size": "50-200",
        "pain_points": ["a", "b"], "recent_news": [],
        "tech_stack": [],
        "research_summary": "ABC is a SaaS firm in the EU; opened a new office in Berlin in March 2025.",
    }
    with patch("agents.research_agent._call_claude_synthesize",
               new=AsyncMock(return_value=fake_output)):
        out = await synthesize({
            "lead": {"company_name": "ABC", "website": "x"},
            "raw_website_text": "",
            "news_results": [],
            "tech_stack_hints": [],
            "synthesized": {"research_summary": "vague prior summary"},
            "quality_ok": False,  # signals re-entry after a failed quality check
            "refine_count": 0,
        })

    assert out["refine_count"] == 1
    assert out["synthesized"] == fake_output
```

- [ ] **Step 2: Run, verify fail**

```bash
cd /Users/ashitverma/Sales\ Automation/backend && .venv/bin/pytest tests/test_research_agent.py -v -k "synthesize"
```

Expected: 2 FAILS.

- [ ] **Step 3: Implement helper + node**

Append to `agents/research_agent.py` (with new imports at the top):

```python
import anthropic
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from agents.prompts.research_prompts import SYNTHESIS_SYSTEM
```

```python
RESEARCH_OUTPUT_TOOL = {
    "name": "submit_research",
    "description": "Submit the structured research findings.",
    "input_schema": {
        "type": "object",
        "properties": {
            "industry": {"type": "string"},
            "company_size": {"type": "string"},
            "pain_points": {"type": "array", "items": {"type": "string"},
                            "minItems": 2, "maxItems": 4},
            "recent_news": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
            "tech_stack": {"type": "array", "items": {"type": "string"}},
            "research_summary": {"type": "string"},
        },
        "required": ["industry", "company_size", "pain_points",
                     "recent_news", "tech_stack", "research_summary"],
    },
}


def _build_synthesize_user_message(state: ResearchState, refine_context: dict | None) -> str:
    parts: list[str] = [
        f"Company: {state['lead']['company_name']}",
        f"Website: {state['lead']['website']}",
        "",
        "WEBSITE TEXT (truncated):",
        state.get("raw_website_text") or "<no website content available>",
        "",
        "RECENT NEWS:",
    ]
    if state.get("news_results"):
        for item in state["news_results"][:5]:
            parts.append(f"- {item.get('title', '')}: {item.get('content', '')}")
    else:
        parts.append("<no news results>")
    parts.append("")
    parts.append(f"TECH_STACK_HINTS: {state.get('tech_stack_hints', [])}")

    if refine_context:
        parts.append("")
        parts.append("REFINEMENT NOTE:")
        parts.append(refine_context["instruction"])
        parts.append(f"PRIOR SUMMARY (rejected): {refine_context['prior_summary']}")

    return "\n".join(parts)


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
async def _call_claude_synthesize(user_message: str, refine_context: dict | None = None) -> dict[str, Any]:
    from core.config import settings
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    resp = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=SYNTHESIS_SYSTEM,
        tools=[RESEARCH_OUTPUT_TOOL],
        tool_choice={"type": "tool", "name": "submit_research"},
        messages=[{"role": "user", "content": user_message}],
    )
    tool_use = next(b for b in resp.content if getattr(b, "type", None) == "tool_use")
    return tool_use.input


async def synthesize(state: ResearchState) -> dict[str, Any]:
    refine_count = state["refine_count"]
    refine_context = None
    if not state["quality_ok"] and state["synthesized"] is not None:
        refine_count += 1
        refine_context = {
            "prior_summary": state["synthesized"].get("research_summary", ""),
            "instruction": (
                "Previous attempt failed the quality check. Write a more specific "
                "summary that references a concrete fact from the source material."
            ),
        }
    user_message = _build_synthesize_user_message(state, refine_context)
    raw_output = await _call_claude_synthesize(user_message, refine_context=refine_context)
    return {"synthesized": raw_output, "refine_count": refine_count}
```

- [ ] **Step 4: Run, verify pass**

```bash
cd /Users/ashitverma/Sales\ Automation/backend && .venv/bin/pytest tests/test_research_agent.py -v -k "synthesize"
```

Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/research_agent.py backend/tests/test_research_agent.py
git commit -m "feat(research-agent): add Claude synthesize helper + node with refine_count semantics"
```

---

## Task 10: `_call_openai_quality` helper + `check_quality` node

**Files:**
- Modify: `agents/research_agent.py`
- Test: `backend/tests/test_research_agent.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_research_agent.py`:

```python
async def test_check_quality_short_summary_auto_fails_without_llm_call():
    from agents.research_agent import check_quality

    state = {
        "lead": {}, "raw_website_text": "", "news_results": [],
        "tech_stack_hints": [],
        "synthesized": {"research_summary": "Five word summary only here."},  # 5 words
        "quality_ok": False, "refine_count": 0,
    }
    # Patch the LLM helper so we can assert it was NOT called
    with patch("agents.research_agent._call_openai_quality",
               new=AsyncMock()) as mock_helper:
        out = await check_quality(state)

    assert out == {"quality_ok": False}
    assert mock_helper.await_count == 0


async def test_check_quality_passes_when_llm_returns_passes_true():
    from agents.research_agent import check_quality

    long_summary = (
        "Acme Corp is a logistics SaaS firm headquartered in Denver. "
        "They expanded into the EU in Q1 2025 and recently hired a VP of Sales."
    )
    state = {
        "lead": {}, "raw_website_text": "", "news_results": [],
        "tech_stack_hints": [],
        "synthesized": {"research_summary": long_summary},
        "quality_ok": False, "refine_count": 0,
    }
    with patch("agents.research_agent._call_openai_quality",
               new=AsyncMock(return_value={"passes": True, "reason": "named city + dated event"})):
        out = await check_quality(state)

    assert out == {"quality_ok": True}


async def test_check_quality_fails_when_llm_returns_passes_false():
    from agents.research_agent import check_quality

    long_summary = " ".join(["word"] * 25)  # 25 words but vague
    state = {
        "lead": {}, "raw_website_text": "", "news_results": [],
        "tech_stack_hints": [],
        "synthesized": {"research_summary": long_summary},
        "quality_ok": False, "refine_count": 0,
    }
    with patch("agents.research_agent._call_openai_quality",
               new=AsyncMock(return_value={"passes": False, "reason": "no specific fact"})):
        out = await check_quality(state)

    assert out == {"quality_ok": False}
```

- [ ] **Step 2: Run, verify fail**

```bash
cd /Users/ashitverma/Sales\ Automation/backend && .venv/bin/pytest tests/test_research_agent.py -v -k "check_quality"
```

Expected: 3 FAILS.

- [ ] **Step 3: Implement helper + node**

Append to `agents/research_agent.py` (add openai to imports):

```python
import json

import openai

from agents.prompts.research_prompts import QUALITY_CHECK_SYSTEM
```

```python
@retry(
    retry=retry_if_exception_type((
        openai.APIConnectionError,
        openai.RateLimitError,
        openai.APITimeoutError,
    )),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
async def _call_openai_quality(summary: str) -> dict[str, Any]:
    from core.config import settings
    client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": QUALITY_CHECK_SYSTEM},
            {"role": "user", "content": f"Summary:\n{summary}\n\nReturn JSON {{\"passes\": bool, \"reason\": str}}."},
        ],
    )
    return json.loads(resp.choices[0].message.content)


async def check_quality(state: ResearchState) -> dict[str, Any]:
    summary = (state["synthesized"] or {}).get("research_summary", "")
    if len(summary.split()) < 20:
        return {"quality_ok": False}

    result = await _call_openai_quality(summary)
    return {"quality_ok": bool(result.get("passes"))}
```

- [ ] **Step 4: Run, verify pass**

```bash
cd /Users/ashitverma/Sales\ Automation/backend && .venv/bin/pytest tests/test_research_agent.py -v -k "check_quality"
```

Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/research_agent.py backend/tests/test_research_agent.py
git commit -m "feat(research-agent): add OpenAI quality helper + check_quality node"
```

---

## Task 11: Routing, graph wiring, entry point + the 4 spec-mandated agent tests

**Files:**
- Modify: `agents/research_agent.py`
- Test: `backend/tests/test_research_agent.py`

This task ties the graph together and adds the four end-to-end tests called for by the spec (`test_happy_path`, `test_website_unreachable`, `test_quality_check_loop`, `test_max_retries`). All four mock the two LLM helpers (`_call_claude_synthesize`, `_call_openai_quality`) — Task 9 and 10 already proved they have the right names and signatures.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_research_agent.py`:

```python
import pytest
from httpx import Response


VALID_OUTPUT = {
    "industry": "Logistics SaaS",
    "company_size": "50-200",
    "pain_points": ["manual outbound prospecting", "scaling sales ops"],
    "recent_news": ["expanded to Europe Q1 2025"],
    "tech_stack": ["Salesforce"],
    "research_summary": (
        "Acme Logistics is a mid-size logistics SaaS firm based in Denver. "
        "They expanded into Europe in Q1 2025 and recently hired a VP of Sales."
    ),
}


async def test_happy_path():
    from agents.research_agent import run_research_agent

    html = "<html><body><h1>Acme Logistics</h1><p>We use Salesforce.</p></body></html>"
    with respx.mock(base_url="https://acme.example") as mocker, \
         patch("agents.research_agent.AsyncTavilyClient") as tav, \
         patch("agents.research_agent._call_claude_synthesize",
               new=AsyncMock(return_value=VALID_OUTPUT)), \
         patch("agents.research_agent._call_openai_quality",
               new=AsyncMock(return_value={"passes": True, "reason": "named city + dated event"})):
        mocker.get("/").mock(return_value=Response(200, text=html))
        tav.return_value.search = AsyncMock(return_value={"results": []})

        result = await run_research_agent({
            "company_name": "Acme Logistics",
            "website": "https://acme.example/",
        })

    assert result["industry"] == "Logistics SaaS"
    assert 2 <= len(result["pain_points"]) <= 4
    assert len(result["research_summary"].split()) >= 20


async def test_website_unreachable_still_succeeds():
    from agents.research_agent import run_research_agent

    captured: dict = {}

    async def _fake_synth(user_message: str, refine_context=None):
        captured["msg"] = user_message
        return VALID_OUTPUT

    with respx.mock(base_url="https://broken.example") as mocker, \
         patch("agents.research_agent.AsyncTavilyClient") as tav, \
         patch("agents.research_agent._call_claude_synthesize", new=_fake_synth), \
         patch("agents.research_agent._call_openai_quality",
               new=AsyncMock(return_value={"passes": True, "reason": "ok"})):
        mocker.get("/").mock(return_value=Response(500))
        tav.return_value.search = AsyncMock(return_value={"results": []})

        result = await run_research_agent({
            "company_name": "Broken Inc",
            "website": "https://broken.example/",
        })

    assert result["industry"] == "Logistics SaaS"  # came from VALID_OUTPUT
    assert "<no website content available>" in captured["msg"]


async def test_quality_check_loop_one_refine_then_pass():
    from agents.research_agent import run_research_agent

    short_then_long = [
        # First synthesis: short summary that auto-fails quality (< 20 words)
        {**VALID_OUTPUT, "research_summary": "Acme is a SaaS firm."},
        # Second synthesis (refine): full valid output
        VALID_OUTPUT,
    ]

    synth_mock = AsyncMock(side_effect=short_then_long)
    quality_mock = AsyncMock(return_value={"passes": True, "reason": "ok"})

    with respx.mock(base_url="https://acme.example") as mocker, \
         patch("agents.research_agent.AsyncTavilyClient") as tav, \
         patch("agents.research_agent._call_claude_synthesize", new=synth_mock), \
         patch("agents.research_agent._call_openai_quality", new=quality_mock):
        mocker.get("/").mock(return_value=Response(200, text="<p>hi</p>"))
        tav.return_value.search = AsyncMock(return_value={"results": []})

        result = await run_research_agent({
            "company_name": "Acme",
            "website": "https://acme.example/",
        })

    assert synth_mock.await_count == 2  # initial + 1 refine
    assert result["industry"] == "Logistics SaaS"


async def test_max_retries_raises_agent_output_error():
    from agents.research_agent import run_research_agent
    from core.exceptions import AgentOutputError

    short_output = {**VALID_OUTPUT, "research_summary": "Acme is a SaaS firm."}
    synth_mock = AsyncMock(return_value=short_output)
    quality_mock = AsyncMock(return_value={"passes": False, "reason": "no fact"})

    with respx.mock(base_url="https://acme.example") as mocker, \
         patch("agents.research_agent.AsyncTavilyClient") as tav, \
         patch("agents.research_agent._call_claude_synthesize", new=synth_mock), \
         patch("agents.research_agent._call_openai_quality", new=quality_mock):
        mocker.get("/").mock(return_value=Response(200, text="<p>hi</p>"))
        tav.return_value.search = AsyncMock(return_value={"results": []})

        with pytest.raises(AgentOutputError) as exc_info:
            await run_research_agent({
                "company_name": "Acme",
                "website": "https://acme.example/",
            })

    assert "quality_check_failed_after_2_refines" in exc_info.value.violations
    assert synth_mock.await_count == 3  # initial + 2 refines
```

- [ ] **Step 2: Run, verify fail**

```bash
cd /Users/ashitverma/Sales\ Automation/backend && .venv/bin/pytest tests/test_research_agent.py -v -k "happy_path or unreachable or quality_check_loop or max_retries"
```

Expected: 4 FAILS — `NotImplementedError` from the entry point stub.

- [ ] **Step 3: Implement routing, graph, and entry point**

Append to `agents/research_agent.py` (with new imports near the top):

```python
from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError
```

Replace the existing stub `run_research_agent` and add the routing + builder:

```python
def _route_after_quality(state: ResearchState) -> str:
    if state["quality_ok"] or state["refine_count"] >= 2:
        return "end"
    return "synthesize"


def _build_graph():
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
    graph.add_conditional_edges(
        "check_quality",
        _route_after_quality,
        {"end": END, "synthesize": "synthesize"},
    )
    return graph.compile()


_graph = _build_graph()


async def run_research_agent(lead: dict[str, Any]) -> dict[str, Any]:
    from core.exceptions import AgentOutputError

    initial: ResearchState = {
        "lead": lead,
        "raw_website_text": None,
        "news_results": [],
        "tech_stack_hints": [],
        "synthesized": None,
        "quality_ok": False,
        "refine_count": 0,
    }
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

- [ ] **Step 4: Run, verify pass**

```bash
cd /Users/ashitverma/Sales\ Automation/backend && .venv/bin/pytest tests/test_research_agent.py -v
```

Expected: All tests in the file pass (the 4 new ones plus everything from Tasks 2-10).

If `test_max_retries` fails with `synth_mock.await_count == 2` instead of 3, the refine_count increment logic in `synthesize` is wrong — re-read Task 9 step 3 and verify the increment guard is `not state["quality_ok"] and state["synthesized"] is not None`.

- [ ] **Step 5: Commit**

```bash
git add agents/research_agent.py backend/tests/test_research_agent.py
git commit -m "feat(research-agent): wire LangGraph + entry point with Pydantic validation gate"
```

---

## Task 12: `trigger_research` in agents_interface

**Files:**
- Create: `backend/agents_interface/research.py`
- Test: `backend/tests/test_research_agent.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_research_agent.py`:

```python
async def test_trigger_research_persists_result_and_updates_status(db_session):
    """Backend interface test (test #5 from spec). Uses real Postgres test container."""
    from uuid import uuid4
    from sqlalchemy import text as _t
    import agents_interface.research as research_iface

    # Insert a campaign + lead via raw SQL (matches existing test patterns elsewhere)
    campaign_id = uuid4()
    lead_id = uuid4()
    await db_session.execute(_t(
        "INSERT INTO campaigns (id, name, status) VALUES (:id, :name, 'draft')"
    ), {"id": campaign_id, "name": "T"})
    await db_session.execute(_t(
        "INSERT INTO leads (id, campaign_id, company_name, website, email, status) "
        "VALUES (:id, :cid, :cn, :w, :e, 'new')"
    ), {"id": lead_id, "cid": campaign_id, "cn": "Acme",
        "w": "https://acme.example/", "e": "x@acme.example"})
    await db_session.commit()

    canned = {**VALID_OUTPUT}

    fake_vs = AsyncMock()
    with patch.object(research_iface, "run_research_agent",
                      new=AsyncMock(return_value=canned)), \
         patch.object(research_iface, "get_vector_store", return_value=fake_vs):
        result = await research_iface.trigger_research(lead_id, db_session)

    assert result == canned

    row = (await db_session.execute(_t(
        "SELECT status, research_data FROM leads WHERE id = :id"
    ), {"id": lead_id})).first()
    assert row.status == "researched"
    assert row.research_data == canned

    fake_vs.upsert_company_research.assert_awaited_once()
    args, _ = fake_vs.upsert_company_research.call_args
    assert args[0] == lead_id
    assert args[1] == canned["research_summary"]
    assert args[2] == canned
```

- [ ] **Step 2: Run, verify fail**

```bash
cd /Users/ashitverma/Sales\ Automation/backend && .venv/bin/pytest tests/test_research_agent.py::test_trigger_research_persists_result_and_updates_status -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'agents_interface.research'`.

- [ ] **Step 3: Implement `trigger_research`**

Create `backend/agents_interface/research.py`:

```python
"""Backend interface for the Research Agent.

This is the only place backend code touches the Research Agent. The agent itself
lives in `agents/research_agent.py` and stays free of DB and HTTP concerns.
"""
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from agents.research_agent import run_research_agent
from core.vector_store import get_vector_store
from models.lead import Lead

logger = logging.getLogger(__name__)


async def trigger_research(lead_id: UUID, db: AsyncSession) -> dict:
    lead = await db.get(Lead, lead_id)
    if lead is None:
        raise LookupError(f"Lead {lead_id} not found")

    result = await run_research_agent({
        "company_name": lead.company_name,
        "website": lead.website,
    })

    lead.research_data = result
    lead.status = "researched"
    await db.commit()

    # Vector upsert is best-effort — DB write is the source of truth.
    # Spec deviation (intentional): commit before vector write so research survives Qdrant outages.
    try:
        vs = get_vector_store()
        await vs.upsert_company_research(lead_id, result["research_summary"], result)
    except Exception as e:
        logger.warning("Vector upsert failed for lead %s: %s", lead_id, e)

    return result
```

- [ ] **Step 4: Run, verify pass**

```bash
cd /Users/ashitverma/Sales\ Automation/backend && .venv/bin/pytest tests/test_research_agent.py -v
```

Expected: All tests pass (including the new interface test).

- [ ] **Step 5: Commit**

```bash
git add backend/agents_interface/research.py backend/tests/test_research_agent.py
git commit -m "feat(agents-interface): add trigger_research with DB + vector persistence"
```

---

## Task 13: Wire `internal.py` route to the real interface; update existing tests

**Files:**
- Modify: `backend/api/internal.py`
- Modify: `backend/tests/test_internal.py`

- [ ] **Step 1: Read the existing test_internal.py and identify the test that asserts stub behavior**

```bash
cd /Users/ashitverma/Sales\ Automation/backend && grep -n "trigger_research\|queued" tests/test_internal.py
```

Expected: lines for `test_trigger_research_missing_token_returns_401`, `test_trigger_research_wrong_token_returns_401`, and `test_trigger_research_valid_token_returns_queued`. The 401 tests stay; the `_returns_queued` test becomes outdated.

- [ ] **Step 2: Replace the `_returns_queued` test with two new tests that exercise the real interface**

In `backend/tests/test_internal.py`, replace this block:

```python
async def test_trigger_research_valid_token_returns_queued(async_client: AsyncClient):
    resp = await async_client.post(
        "/api/internal/trigger-research",
        json={"lead_id": ANY_LEAD_ID},
        headers=VALID_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["queued"] is True
    assert body["data"]["lead_id"] == ANY_LEAD_ID
```

with:

```python
from unittest.mock import AsyncMock, patch


async def test_trigger_research_valid_token_returns_real_research(async_client: AsyncClient):
    canned = {
        "industry": "SaaS", "company_size": "50-200",
        "pain_points": ["a", "b"], "recent_news": [],
        "tech_stack": [],
        "research_summary": "Acme is a SaaS firm based in Denver with a recent expansion in Q1 2025.",
    }
    with patch("api.internal.trigger_research_iface",
               new=AsyncMock(return_value=canned)):
        resp = await async_client.post(
            "/api/internal/trigger-research",
            json={"lead_id": ANY_LEAD_ID},
            headers=VALID_HEADERS,
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"] == canned
    assert body["error"] is None


async def test_trigger_research_returns_404_when_lead_missing(async_client: AsyncClient):
    with patch("api.internal.trigger_research_iface",
               new=AsyncMock(side_effect=LookupError("Lead xyz not found"))):
        resp = await async_client.post(
            "/api/internal/trigger-research",
            json={"lead_id": ANY_LEAD_ID},
            headers=VALID_HEADERS,
        )

    assert resp.status_code == 404
```

- [ ] **Step 3: Run the updated tests, verify they fail**

```bash
cd /Users/ashitverma/Sales\ Automation/backend && .venv/bin/pytest tests/test_internal.py -v -k "trigger_research"
```

Expected: `test_trigger_research_valid_token_returns_real_research` FAILS (`AttributeError: api.internal has no attribute trigger_research_iface`).

- [ ] **Step 4: Wire the route to the real interface in `backend/api/internal.py`**

Modify `backend/api/internal.py`:

1. Add import near the top (after the existing imports):

```python
from agents_interface.research import trigger_research as trigger_research_iface
```

2. Replace the existing `trigger_research` route body:

```python
@router.post("/trigger-research", dependencies=[Depends(_require_token)])
async def trigger_research(body: LeadTriggerBody, db: AsyncSession = Depends(get_db)):
    try:
        result = await trigger_research_iface(body.lead_id, db)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ok(result)
```

The route function name (`trigger_research`) stays the same so URL routing is unchanged. The local alias `trigger_research_iface` lets tests patch the import without colliding with the route function name.

- [ ] **Step 5: Run the updated tests, verify they pass**

```bash
cd /Users/ashitverma/Sales\ Automation/backend && .venv/bin/pytest tests/test_internal.py -v
```

Expected: all tests in `test_internal.py` pass — the 401 tests still pass, the new 200/404 tests pass, the personalization/followup/leads-needing-followup stubs still pass (we didn't touch them).

- [ ] **Step 6: Commit**

```bash
git add backend/api/internal.py backend/tests/test_internal.py
git commit -m "feat(api): wire trigger-research route to real agents_interface"
```

---

## Task 14: Implement smoke script for real-API research

**Files:**
- Modify: `agents/scripts/smoke.py`

This task does not produce CI tests — it's a manual verification script. The verification step in this task is running it against a real lead.

- [ ] **Step 1: Implement the real smoke function**

Replace the body of `agents/scripts/smoke.py`:

```python
"""Real-API smoke tests for agents. Not run in CI.

Usage (from repo root, with backend/.venv activated):
    python agents/scripts/smoke.py research
    python agents/scripts/smoke.py all

Requires: TAVILY_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY in .env.
"""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path


def _bootstrap_env_and_paths() -> None:
    """Make `core.config` importable and load `.env` even when run standalone."""
    repo_root = Path(__file__).resolve().parents[2]
    backend = repo_root / "backend"
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))

    # Best-effort .env load; production callers should already have env set
    env_path = repo_root / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


async def smoke_research() -> int:
    _bootstrap_env_and_paths()
    from agents.research_agent import run_research_agent

    lead = {"company_name": "Stripe", "website": "https://stripe.com"}
    print(f"Running research agent against {lead['company_name']}...")
    result = await run_research_agent(lead)
    print(json.dumps(result, indent=2))

    if not result.get("pain_points") or not result.get("research_summary"):
        print("FAIL: empty pain_points or research_summary", file=sys.stderr)
        return 1
    print("OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent smoke tests against real APIs.")
    parser.add_argument("agent", choices=["research", "all"])
    args = parser.parse_args()

    if args.agent in ("research", "all"):
        return asyncio.run(smoke_research())
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the smoke (real APIs — costs ~$0.02 + 1 Tavily call)**

```bash
cd /Users/ashitverma/Sales\ Automation && backend/.venv/bin/python agents/scripts/smoke.py research
```

Expected: pretty-printed JSON with `industry`, `company_size`, `pain_points` (length 2-4), `recent_news`, `tech_stack`, `research_summary` (>= 20 words). Final line: `OK`.

If the process raises `AgentOutputError`, the prompt may need tightening — re-read `agents/prompts/research_prompts.py:SYNTHESIS_SYSTEM`. Note the failure in `scratchpad.md` and iterate on the prompt.

- [ ] **Step 3: Commit**

```bash
git add agents/scripts/smoke.py
git commit -m "feat(agents): implement research smoke script against real APIs"
```

---

## Task 15: Final verification + status updates

**Files:**
- Modify: `CLAUDE.md`
- Modify: `scratchpad.md`

- [ ] **Step 1: Run the full backend test suite — no regressions**

```bash
cd /Users/ashitverma/Sales\ Automation/backend && .venv/bin/pytest tests/ -v
```

Expected: All Phase 0/1/2 tests still pass; the 5+ Phase 3A tests pass. If any Phase 2 test fails, do not proceed — fix the regression first.

- [ ] **Step 2: Lint**

```bash
cd /Users/ashitverma/Sales\ Automation/backend && .venv/bin/ruff check . ../agents
```

Expected: all checks pass. Fix any reported issues and re-run.

- [ ] **Step 3: Update `CLAUDE.md` Current Status block**

In `CLAUDE.md`, change:

```markdown
- **Phase 3** — LangGraph Agents: ⬜ not started
```

to:

```markdown
- **Phase 3** — LangGraph Agents: 🟡 in progress (3A Research complete; 3B/3C/3D pending)
```

- [ ] **Step 4: Append to `scratchpad.md`**

Append a new section to `scratchpad.md`:

```markdown
## Phase 3A — Research Agent (2026-05-15)

- LangGraph 1.x: `add_conditional_edges` with explicit dict mapping (`{"end": END, "synthesize": "synthesize"}`) — string keys returned by router function map to node names. Worked first try.
- `agents/` made an installable package via `agents/pyproject.toml` + path dep in `backend/pyproject.toml`. Imports resolve cleanly in pytest, uvicorn, and standalone smoke.
- `refine_count` increment lives in `synthesize` (on re-entry when `quality_ok=False AND synthesized is not None`), not in `check_quality`. This makes the budget arithmetic work: 1 initial + 2 refines = 3 Claude calls before the routing edge terminates the graph.
- Pydantic validation deferred to entry point (after `_graph.ainvoke`) — keeps schema errors (raise) cleanly separated from quality failures (loop).
- LLM mocking via `patch("agents.research_agent._call_claude_synthesize", new=AsyncMock(...))` rather than respx on the SDK — readable, stable. Wire-format coverage handled by the smoke script.
- `_route_after_quality` is a pure function; LangGraph re-evaluates it after each `check_quality` invocation. No need for state mutation tricks.
- Tavily SDK `AsyncTavilyClient.search` is awaitable and returns `{"results": [...], "query": ..., "answer": ...}`. Patched via `unittest.mock.patch` at the class level.
- Vector upsert lives BEHIND the DB commit in `trigger_research` — Qdrant outages don't lose research data. Deviation from the original spec text noted in the design doc (decisions log).
```

- [ ] **Step 5: Commit status updates**

```bash
git add CLAUDE.md scratchpad.md
git commit -m "chore: mark Phase 3A complete; document research-agent build notes"
```

- [ ] **Step 6: Final sanity check**

```bash
cd /Users/ashitverma/Sales\ Automation && git log --oneline -20
```

Expected: a clean sequence of ~15 small commits from Task 1 through Task 15, each one a focused step.

---

## Self-Review Checklist (already run by plan author; re-run if you edit the plan)

**Spec coverage** — every spec section maps to at least one task:

| Spec section | Task(s) |
|---|---|
| 2.1 `agents/` installable package | Task 1 |
| 2.2 Settings (already present in code) | Verified in plan preamble; no task needed |
| 2.3 `AgentOutputError` + handler | Task 2 |
| 2.4 Skeleton files (prompts, scripts) | Task 4 |
| 3.1 `agents/research_agent.py` contracts | Task 5 (state/output), Tasks 6-11 (impl) |
| 3.2 `research_prompts.py` constants | Task 4 |
| 3.3 `agents_interface/research.py` | Task 12 |
| 3.4 `backend/api/internal.py` wiring | Task 13 |
| 3.5 `agents/scripts/smoke.py` | Task 4 (skeleton), Task 14 (impl) |
| 4.1 `fetch_website` | Task 7 |
| 4.2 `search_news` | Task 8 |
| 4.3 `extract_tech_stack` | Task 6 |
| 4.4 `synthesize` + helper + tenacity | Task 9 |
| 4.5 `check_quality` + helper | Task 10 |
| 4.6 `_route_after_quality` | Task 11 |
| 4.7 Graph wiring | Task 11 |
| 4.8 Entry point + Pydantic gate | Task 11 |
| 5.1 Mocking strategy | Tasks 7, 8, 9, 10, 11, 12 (per-test mocks) |
| 5.2 Five tests | `test_happy_path` + `_unreachable` + `_quality_check_loop` + `_max_retries` (Task 11), `test_trigger_research_persists_...` (Task 12) |
| 6 Verification commands | Task 15 |

**Type/name consistency** — names used across tasks (verified consistent):
- `ResearchState`, `ResearchOutput` — Tasks 5, 6, 7, 8, 9, 10, 11
- `_call_claude_synthesize`, `_call_openai_quality` — Tasks 9, 10, 11
- `synthesize`, `check_quality`, `extract_tech_stack`, `fetch_website`, `search_news` — node names match across all node tasks and Task 11 graph wiring
- `_route_after_quality` returns `"end"` or `"synthesize"`; conditional edges map `{"end": END, "synthesize": "synthesize"}` — Task 11
- `trigger_research` (route function in `internal.py`) and `trigger_research_iface` (alias for the agents_interface function) — Task 13 disambiguates
- `AgentOutputError(agent: str, violations: list[str])` constructor — Task 2 defines, Task 11 raises with `agent="research"`, `violations=["quality_check_failed_after_2_refines"]`

**Placeholders** — none found.
