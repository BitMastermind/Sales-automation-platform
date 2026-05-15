"""Tests for the Reply Classifier agent (Phase 3D)."""
import json

import pytest
import respx
from httpx import Response


@pytest.fixture(autouse=True)
def _stub_openai_key(monkeypatch):
    from core.config import settings
    monkeypatch.setattr(settings, "openai_api_key", "sk-test-classifier")


def _openai_chat_response(payload: dict) -> Response:
    return Response(
        200,
        json={
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 0,
            "model": "gpt-4o-mini",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": json.dumps(payload)},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        },
    )


async def test_interested_signal():
    from agents.reply_classifier import run_reply_classifier

    with respx.mock:
        respx.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=_openai_chat_response(
                {
                    "intent": "interested",
                    "confidence": 0.92,
                    "suggested_next_action": "schedule_call",
                    "key_phrases": ["sounds great", "let's talk next week"],
                }
            )
        )
        result = await run_reply_classifier("Sounds great, let's talk next week")

    assert result.intent == "interested"
    assert result.suggested_next_action == "schedule_call"
    assert 0.0 <= result.confidence <= 1.0
    assert "sounds great" in [p.lower() for p in result.key_phrases]


async def test_unsubscribe():
    from agents.reply_classifier import run_reply_classifier

    with respx.mock:
        respx.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=_openai_chat_response(
                {
                    "intent": "unsubscribe",
                    "confidence": 0.97,
                    "suggested_next_action": "unsubscribe_lead",
                    "key_phrases": ["remove me from your list"],
                }
            )
        )
        result = await run_reply_classifier("Please remove me from your list")

    assert result.intent == "unsubscribe"
    assert result.suggested_next_action == "unsubscribe_lead"


async def test_not_interested():
    from agents.reply_classifier import run_reply_classifier

    with respx.mock:
        respx.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=_openai_chat_response(
                {
                    "intent": "not_interested",
                    "confidence": 0.88,
                    "suggested_next_action": "close_lead",
                    "key_phrases": ["not relevant"],
                }
            )
        )
        result = await run_reply_classifier("Not relevant for us right now")

    assert result.intent == "not_interested"
    assert result.suggested_next_action == "close_lead"


async def test_ambiguous_unknown():
    """Ambiguous reply -> intent=unknown. Validator silently corrects a
    mismatched action (LLM returns 'schedule_call' but unknown must map to 'wait')."""
    from agents.reply_classifier import run_reply_classifier

    with respx.mock:
        respx.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=_openai_chat_response(
                {
                    "intent": "unknown",
                    "confidence": 0.42,
                    "suggested_next_action": "schedule_call",
                    "key_phrases": ["OK"],
                }
            )
        )
        result = await run_reply_classifier("OK")

    assert result.intent == "unknown"
    assert result.suggested_next_action == "wait"


async def test_lead_status_updated_on_interest(db_session):
    from datetime import datetime, timezone

    from agents_interface.classifier import classify_reply
    from models.campaign import Campaign
    from models.email import Email
    from models.lead import Lead
    from models.reply import Reply

    campaign = Campaign(name="Classifier Campaign")
    db_session.add(campaign)
    await db_session.flush()

    lead = Lead(campaign_id=campaign.id, company_name="Acme", email="ceo@acme.com")
    db_session.add(lead)
    await db_session.flush()

    email = Email(
        lead_id=lead.id,
        subject="Hi",
        body="Original outreach body",
        type="outreach",
        sent_at=datetime.now(timezone.utc),
    )
    db_session.add(email)
    await db_session.flush()

    reply = Reply(email_id=email.id, content="Sounds great, let's talk next week")
    db_session.add(reply)
    await db_session.commit()

    with respx.mock:
        respx.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=_openai_chat_response(
                {
                    "intent": "interested",
                    "confidence": 0.93,
                    "suggested_next_action": "schedule_call",
                    "key_phrases": ["sounds great"],
                }
            )
        )
        result = await classify_reply(reply.id, db_session)

    assert result.intent == "interested"

    await db_session.refresh(lead)
    await db_session.refresh(reply)
    assert lead.status == "meeting_booked"
    assert reply.classified_as == "interested"
