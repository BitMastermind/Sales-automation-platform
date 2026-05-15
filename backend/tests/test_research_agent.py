"""Tests for the Research Agent (Phase 3A)."""
import pytest
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


# ---------------------------------------------------------------------------
# Task 11 — end-to-end graph tests
# ---------------------------------------------------------------------------

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
