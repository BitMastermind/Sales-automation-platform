"""Tests for the Follow-up Agent (Phase 3D)."""
from unittest.mock import AsyncMock, patch

import pytest

ORIGINAL_EMAIL = {"subject": "Quick question", "body": "Hi, I wanted to reach out about your recent expansion."}
RESEARCH = {
    "industry": "Logistics SaaS",
    "company_size": "50-200",
    "pain_points": ["scaling outbound", "manual ops"],
    "research_summary": "Acme is a logistics SaaS firm expanding to Europe.",
}


def _canned_body(word_count: int) -> dict:
    return {"subject": "Following up", "body": " ".join(["word"] * word_count)}


async def test_day_3_bump():
    """days=3 → strategy day_3_bump, should_send=True, body ≤ 40 words."""
    from agents.followup_agent import run_followup_agent

    with patch(
        "agents.followup_agent._call_claude_generate",
        new=AsyncMock(return_value=_canned_body(35)),
    ) as mock_gen:
        result = await run_followup_agent(
            lead_id="lead-1",
            days_since_last_touch=3,
            original_email=ORIGINAL_EMAIL,
            prior_followups=[],
            research=RESEARCH,
        )

    assert result.should_send is True
    assert result.strategy == "day_3_bump"
    assert result.subject == "Following up"
    assert result.body is not None
    assert len(result.body.split()) <= 40
    mock_gen.assert_awaited_once()


async def test_day_7_value_add():
    """days=7 → strategy day_7_value_add, should_send=True."""
    from agents.followup_agent import run_followup_agent

    with patch(
        "agents.followup_agent._call_claude_generate",
        new=AsyncMock(return_value={"subject": "A resource for you", "body": "Here is something useful."}),
    ):
        result = await run_followup_agent(
            lead_id="lead-2",
            days_since_last_touch=7,
            original_email=ORIGINAL_EMAIL,
            prior_followups=[],
            research=RESEARCH,
        )

    assert result.should_send is True
    assert result.strategy == "day_7_value_add"
    assert result.subject is not None


async def test_day_14_breakup():
    """days=14 → strategy day_14_breakup, body ≤ 30 words."""
    from agents.followup_agent import run_followup_agent

    with patch(
        "agents.followup_agent._call_claude_generate",
        new=AsyncMock(return_value=_canned_body(28)),
    ):
        result = await run_followup_agent(
            lead_id="lead-3",
            days_since_last_touch=14,
            original_email=ORIGINAL_EMAIL,
            prior_followups=[],
            research=RESEARCH,
        )

    assert result.should_send is True
    assert result.strategy == "day_14_breakup"
    assert result.body is not None
    assert len(result.body.split()) <= 30


async def test_stop_after_14():
    """days=15 → should_send=False, strategy=stop, LLM never called."""
    from agents.followup_agent import run_followup_agent

    with patch(
        "agents.followup_agent._call_claude_generate",
        new=AsyncMock(),
    ) as mock_gen:
        result = await run_followup_agent(
            lead_id="lead-4",
            days_since_last_touch=15,
            original_email=ORIGINAL_EMAIL,
            prior_followups=[],
            research=RESEARCH,
        )

    assert result.should_send is False
    assert result.strategy == "stop"
    assert result.subject is None
    assert result.body is None
    mock_gen.assert_not_awaited()


async def test_avoids_repeating_strategy():
    """prior_followups contains day_3_bump → system prompt includes 'Adjust the angle slightly'."""
    from agents.followup_agent import run_followup_agent

    prior_followups = [{"type": "day_3_bump", "body": "Just bumping this up."}]
    captured: list[str] = []

    async def _fake_generate(system_prompt: str, user_message: str) -> dict:
        captured.append(system_prompt)
        return _canned_body(30)

    with patch("agents.followup_agent._call_claude_generate", new=_fake_generate):
        result = await run_followup_agent(
            lead_id="lead-5",
            days_since_last_touch=3,
            original_email=ORIGINAL_EMAIL,
            prior_followups=prior_followups,
            research=RESEARCH,
        )

    assert result.should_send is True
    assert len(captured) == 1
    assert "Adjust the angle slightly" in captured[0]
