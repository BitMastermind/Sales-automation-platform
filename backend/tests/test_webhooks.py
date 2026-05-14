from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.campaign import Campaign
from models.email import Email
from models.lead import Lead


async def _seed_email_with_gmail_id(db_session: AsyncSession, gmail_message_id: str) -> dict:
    campaign = Campaign(name="Webhook Campaign")
    db_session.add(campaign)
    await db_session.flush()

    lead = Lead(campaign_id=campaign.id, company_name="Acme", email="ceo@acme.com")
    db_session.add(lead)
    await db_session.flush()

    email = Email(
        lead_id=lead.id,
        subject="Hi",
        body="Hello",
        type="outreach",
        gmail_message_id=gmail_message_id,
        sent_at=datetime.now(timezone.utc),
    )
    db_session.add(email)
    await db_session.commit()
    return {"email_id": str(email.id), "lead_id": str(lead.id)}


async def test_reply_received_happy_path(async_client: AsyncClient, db_session: AsyncSession):
    ids = await _seed_email_with_gmail_id(db_session, "gmail-msg-001")

    resp = await async_client.post(
        "/api/webhooks/n8n/reply-received",
        json={
            "gmail_message_id": "gmail-msg-001",
            "reply_text": "Very interested!",
            "received_at": "2024-01-15T10:00:00Z",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["classified_as"] == "unknown"
    assert "reply_id" in body["data"]
    assert body["error"] is None


async def test_reply_received_unknown_gmail_id_returns_404(async_client: AsyncClient):
    resp = await async_client.post(
        "/api/webhooks/n8n/reply-received",
        json={
            "gmail_message_id": "nonexistent-message-id",
            "reply_text": "Hello",
            "received_at": "2024-01-15T10:00:00Z",
        },
    )
    assert resp.status_code == 404
    body = resp.json()
    assert body["detail"]["error"]["code"] == "EMAIL_NOT_FOUND"


async def test_email_opened_updates_opened_at(async_client: AsyncClient, db_session: AsyncSession):
    ids = await _seed_email_with_gmail_id(db_session, "gmail-msg-002")

    resp = await async_client.post(
        "/api/webhooks/n8n/email-opened",
        json={
            "email_id": ids["email_id"],
            "opened_at": "2024-01-15T11:00:00Z",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["error"] is None


async def test_email_opened_unknown_email_returns_404(async_client: AsyncClient):
    resp = await async_client.post(
        "/api/webhooks/n8n/email-opened",
        json={
            "email_id": "00000000-0000-0000-0000-000000000000",
            "opened_at": "2024-01-15T11:00:00Z",
        },
    )
    assert resp.status_code == 404
