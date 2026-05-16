"""Tests for the Follow-up Agent (Phase 3D)."""
from unittest.mock import AsyncMock, call, patch

import pytest

ORIGINAL_EMAIL = {"subject": "Quick question about Acme", "body": "Hi Jane, ..."}
RESEARCH = {"research_summary": "Acme Corp is a logistics SaaS firm.", "pain_points": ["manual outbound"]}


def _mock_llm_response(body: str, subject: str = "Re: following up") -> dict:
    return {"subject": subject, "body": body}


async def test_day_3_bump():
    """days=3 → strategy day_3_bump, should_send=True, body ≤ 40 words."""
    from agents.followup_agent import run_followup_agent

    short_body = " ".join(["word"] * 15)  # 15 words — well under 40
    with patch(
        "agents.followup_agent._call_claude_generate",
        new=AsyncMock(return_value=_mock_llm_response(short_body)),
    ):
        result = await run_followup_agent(
            lead_id="lead-1",
            days_since_last_touch=3,
            original_email=ORIGINAL_EMAIL,
            prior_followups=[],
            research=RESEARCH,
        )

    assert result.strategy == "day_3_bump"
    assert result.should_send is True
    assert result.subject is not None
    assert len(result.body.split()) <= 40


async def test_day_7_value_add():
    """days=7 → strategy day_7_value_add, should_send=True."""
    from agents.followup_agent import run_followup_agent

    with patch(
        "agents.followup_agent._call_claude_generate",
        new=AsyncMock(return_value=_mock_llm_response("A short value-add sentence here.")),
    ):
        result = await run_followup_agent(
            lead_id="lead-1",
            days_since_last_touch=7,
            original_email=ORIGINAL_EMAIL,
            prior_followups=[],
            research=RESEARCH,
        )

    assert result.strategy == "day_7_value_add"
    assert result.should_send is True


async def test_day_14_breakup():
    """days=14 → strategy day_14_breakup, should_send=True, body ≤ 30 words."""
    from agents.followup_agent import run_followup_agent

    short_body = " ".join(["word"] * 20)  # 20 words — under 30
    with patch(
        "agents.followup_agent._call_claude_generate",
        new=AsyncMock(return_value=_mock_llm_response(short_body)),
    ):
        result = await run_followup_agent(
            lead_id="lead-1",
            days_since_last_touch=14,
            original_email=ORIGINAL_EMAIL,
            prior_followups=[],
            research=RESEARCH,
        )

    assert result.strategy == "day_14_breakup"
    assert result.should_send is True
    assert len(result.body.split()) <= 30


async def test_stop_after_14():
    """days=15 → should_send=False, strategy='stop', no LLM call."""
    from agents.followup_agent import run_followup_agent

    with patch(
        "agents.followup_agent._call_claude_generate",
        new=AsyncMock(),
    ) as mock_llm:
        result = await run_followup_agent(
            lead_id="lead-1",
            days_since_last_touch=15,
            original_email=ORIGINAL_EMAIL,
            prior_followups=[],
            research=RESEARCH,
        )

    assert result.should_send is False
    assert result.strategy == "stop"
    mock_llm.assert_not_called()


async def test_avoids_repeating_strategy():
    """Prior followup with same strategy → LLM called with 'adjust the angle' in system prompt."""
    from agents.followup_agent import run_followup_agent

    prior = [{"type": "day_3_bump", "body": "Just bumping this up."}]

    captured_system: list[str] = []

    async def fake_generate(user_message: str, system_prompt: str) -> dict:
        captured_system.append(system_prompt)
        return _mock_llm_response(" ".join(["word"] * 10))

    with patch("agents.followup_agent._call_claude_generate", side_effect=fake_generate):
        result = await run_followup_agent(
            lead_id="lead-1",
            days_since_last_touch=3,
            original_email=ORIGINAL_EMAIL,
            prior_followups=prior,
            research=RESEARCH,
        )

    assert result.should_send is True
    assert len(captured_system) == 1
    assert "adjust the angle" in captured_system[0].lower()
