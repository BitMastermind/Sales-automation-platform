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
