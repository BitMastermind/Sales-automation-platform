from datetime import datetime, timezone

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models.campaign import Campaign
from models.email import Email
from models.lead import Lead


async def _seed_email(db_session: AsyncSession) -> dict:
    campaign = Campaign(name="Email Test Campaign")
    db_session.add(campaign)
    await db_session.flush()

    lead = Lead(campaign_id=campaign.id, company_name="Acme", email="ceo@acme.com")
    db_session.add(lead)
    await db_session.flush()

    email = Email(
        lead_id=lead.id,
        subject="Hello",
        body="World",
        type="outreach",
        gmail_message_id="gmsg-email-test",
        sent_at=datetime.now(timezone.utc),
    )
    db_session.add(email)
    await db_session.commit()
    return {"email_id": str(email.id), "lead_id": str(lead.id)}


async def test_list_emails_by_lead(async_client: AsyncClient, db_session: AsyncSession):
    ids = await _seed_email(db_session)

    resp = await async_client.get(f"/api/emails?lead_id={ids['lead_id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 1
    assert body["data"][0]["id"] == ids["email_id"]


async def test_resend_email_returns_queued(async_client: AsyncClient, db_session: AsyncSession):
    ids = await _seed_email(db_session)

    resp = await async_client.post(f"/api/emails/{ids['email_id']}/resend")
    assert resp.status_code == 200
    assert resp.json()["data"]["queued"] is True


async def test_resend_unknown_email_returns_404(async_client: AsyncClient):
    resp = await async_client.post(
        "/api/emails/00000000-0000-0000-0000-000000000000/resend"
    )
    assert resp.status_code == 404
