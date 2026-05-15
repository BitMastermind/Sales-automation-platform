"""Tests for the Personalization Agent (Phase 3B)."""
from unittest.mock import AsyncMock, patch

import pytest

from core.exceptions import AgentOutputError

VALID_RESEARCH = {
    "industry": "Logistics SaaS",
    "company_size": "50-200",
    "pain_points": ["manual outbound", "scaling operations"],
    "recent_news": ["expanded to Europe Q1 2025"],
    "tech_stack": ["Salesforce"],
    "research_summary": (
        "Acme Corp is a logistics SaaS firm that expanded to Europe in Q1 2025 "
        "and recently hired a VP of Sales to scale their outbound motion."
    ),
}

VALID_CAMPAIGN = {
    "product": "OutreachOS",
    "value_prop": "Automates personalized outbound at scale",
    "case_study": "Helped ClosedLoop 3x pipeline in 90 days",
    "tone": "direct",
}

VALID_LEAD = {
    "company_name": "Acme Corp",
    "website": "https://acme.example/",
    "contact_name": "Jane Smith",
    "email": "jane@acme.example",
}

# A clean draft that passes all compliance checks deterministically.
VALID_DRAFT = {
    "subject": "Question about Acme Europe expansion",
    "opening_line": (
        "Saw Acme expanded to Europe in Q1 2025 — that typically triples outbound complexity."
    ),
    "body": (
        "Hi Jane, cross-border outbound at scale is hard. "
        "OutreachOS automates the personalized part without adding headcount. "
        "ClosedLoop tripled their pipeline using it in 90 days. "
        "Given your recent VP of Sales hire and the Europe push, this could save "
        "your team significant manual effort on every sequence step."
    ),
    "cta": "Open to a 15-min chat next week?",
    "full_email": (
        "Question about Acme Europe expansion\n\n"
        "Saw Acme expanded to Europe in Q1 2025 — that typically triples outbound "
        "complexity.\n\n"
        "Hi Jane, cross-border outbound at scale is hard. OutreachOS automates the "
        "personalized part without adding headcount. ClosedLoop tripled their pipeline "
        "using it in 90 days. Given your recent VP of Sales hire and the Europe push, "
        "this could save your team significant manual effort on every sequence step.\n\n"
        "Open to a 15-min chat next week?"
    ),
}


async def test_happy_path():
    """All LLMs mocked → result contains all required email fields."""
    from agents.personalization_agent import run_personalization_agent

    with patch("agents.personalization_agent._call_claude_draft",
               new=AsyncMock(return_value=VALID_DRAFT)), \
         patch("agents.personalization_agent._call_openai_compliance",
               new=AsyncMock(return_value={"violations": []})), \
         patch("agents.personalization_agent.get_vector_store") as mock_vs:
        mock_vs.return_value.get_best_templates = AsyncMock(return_value=[])
        result = await run_personalization_agent(VALID_LEAD, VALID_RESEARCH, VALID_CAMPAIGN)

    assert "subject" in result
    assert "opening_line" in result
    assert "body" in result
    assert "cta" in result
    assert "full_email" in result


async def test_compliance_catches_spam():
    """Draft containing a spam trigger word causes refine to be called."""
    from agents.personalization_agent import run_personalization_agent

    spam_draft = {**VALID_DRAFT, "body": VALID_DRAFT["body"] + " guaranteed results."}
    draft_mock = AsyncMock(side_effect=[spam_draft, VALID_DRAFT])

    with patch("agents.personalization_agent._call_claude_draft", new=draft_mock), \
         patch("agents.personalization_agent._call_openai_compliance",
               new=AsyncMock(return_value={"violations": []})), \
         patch("agents.personalization_agent.get_vector_store") as mock_vs:
        mock_vs.return_value.get_best_templates = AsyncMock(return_value=[])
        result = await run_personalization_agent(VALID_LEAD, VALID_RESEARCH, VALID_CAMPAIGN)

    assert draft_mock.await_count == 2  # initial + 1 refine
    assert "subject" in result


async def test_opening_line_must_match_research():
    """When LLM flags no research overlap in opening_line, refine is triggered."""
    from agents.personalization_agent import run_personalization_agent

    no_overlap_draft = {
        **VALID_DRAFT,
        "opening_line": "I wanted to reach out about your business goals.",
    }
    draft_mock = AsyncMock(side_effect=[no_overlap_draft, VALID_DRAFT])
    compliance_mock = AsyncMock(side_effect=[
        {"violations": ["opening_line does not reference research"]},
        {"violations": []},
    ])

    with patch("agents.personalization_agent._call_claude_draft", new=draft_mock), \
         patch("agents.personalization_agent._call_openai_compliance", new=compliance_mock), \
         patch("agents.personalization_agent.get_vector_store") as mock_vs:
        mock_vs.return_value.get_best_templates = AsyncMock(return_value=[])
        result = await run_personalization_agent(VALID_LEAD, VALID_RESEARCH, VALID_CAMPAIGN)

    assert draft_mock.await_count == 2
    assert compliance_mock.await_count == 2
    assert "subject" in result


async def test_max_refines_raises():
    """Compliance always failing after 2 refines raises AgentOutputError."""
    from agents.personalization_agent import run_personalization_agent

    compliance_mock = AsyncMock(return_value={"violations": ["unverifiable ROI claim"]})

    with patch("agents.personalization_agent._call_claude_draft",
               new=AsyncMock(return_value=VALID_DRAFT)), \
         patch("agents.personalization_agent._call_openai_compliance", new=compliance_mock), \
         patch("agents.personalization_agent.get_vector_store") as mock_vs:
        mock_vs.return_value.get_best_templates = AsyncMock(return_value=[])
        with pytest.raises(AgentOutputError) as exc_info:
            await run_personalization_agent(VALID_LEAD, VALID_RESEARCH, VALID_CAMPAIGN)

    assert exc_info.value.agent == "personalization"
    assert len(exc_info.value.violations) > 0


async def test_word_count_enforced():
    """Draft with body exceeding 200 words triggers a refine via deterministic check."""
    from agents.personalization_agent import run_personalization_agent

    long_body = " ".join(["word"] * 210)
    long_draft = {**VALID_DRAFT, "body": long_body}
    draft_mock = AsyncMock(side_effect=[long_draft, VALID_DRAFT])

    with patch("agents.personalization_agent._call_claude_draft", new=draft_mock), \
         patch("agents.personalization_agent._call_openai_compliance",
               new=AsyncMock(return_value={"violations": []})), \
         patch("agents.personalization_agent.get_vector_store") as mock_vs:
        mock_vs.return_value.get_best_templates = AsyncMock(return_value=[])
        result = await run_personalization_agent(VALID_LEAD, VALID_RESEARCH, VALID_CAMPAIGN)

    assert draft_mock.await_count == 2  # initial + 1 refine
    assert "subject" in result


async def test_no_templates_ok():
    """Qdrant failure during template retrieval still produces a valid email."""
    from agents.personalization_agent import run_personalization_agent

    with patch("agents.personalization_agent._call_claude_draft",
               new=AsyncMock(return_value=VALID_DRAFT)), \
         patch("agents.personalization_agent._call_openai_compliance",
               new=AsyncMock(return_value={"violations": []})), \
         patch("agents.personalization_agent.get_vector_store") as mock_vs:
        mock_vs.return_value.get_best_templates = AsyncMock(
            side_effect=Exception("Qdrant down")
        )
        result = await run_personalization_agent(VALID_LEAD, VALID_RESEARCH, VALID_CAMPAIGN)

    assert "subject" in result
    assert "body" in result
