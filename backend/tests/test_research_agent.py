"""Tests for the Research Agent (Phase 3A)."""
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from core.exceptions import AgentOutputError, register_exception_handlers


async def test_agent_output_error_handler_returns_422_envelope():
    """The AgentOutputError handler returns a 422 with the standard envelope.

    Uses a self-contained FastAPI app so the global app singleton is never mutated.
    """
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/__raise__")
    async def _raise():
        raise AgentOutputError(agent="research", violations=["x"])

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        resp = await client.get("/__raise__")

    assert resp.status_code == 422
    body = resp.json()
    assert body["data"] is None
    assert body["error"]["code"] == "AGENT_OUTPUT_ERROR"
    assert "research" in body["error"]["message"]
    assert body["error"]["details"]["agent"] == "research"
    assert body["error"]["details"]["violations"] == ["x"]
    assert body["meta"] == {}


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
