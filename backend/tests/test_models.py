from uuid import UUID

import pytest
from sqlalchemy import select

from models.campaign import Campaign
from models.email import Email
from models.lead import Lead


async def test_create_campaign(db_session):
    campaign = Campaign(name="Test Campaign")
    db_session.add(campaign)
    await db_session.flush()

    assert campaign.id is not None
    assert isinstance(campaign.id, UUID)
    assert campaign.status == "draft"


async def test_create_lead_with_fk(db_session):
    campaign = Campaign(name="FK Test Campaign")
    db_session.add(campaign)
    await db_session.flush()

    lead = Lead(campaign_id=campaign.id, company_name="Acme Corp", email="ceo@acme.com")
    db_session.add(lead)
    await db_session.flush()

    result = await db_session.execute(select(Lead).where(Lead.id == lead.id))
    fetched = result.scalar_one()
    assert fetched.campaign_id == campaign.id


async def test_lead_email_cascade(db_session):
    campaign = Campaign(name="Cascade Campaign")
    db_session.add(campaign)
    await db_session.flush()

    lead = Lead(campaign_id=campaign.id, company_name="Delete Corp", email="del@test.com")
    db_session.add(lead)
    await db_session.flush()

    email = Email(lead_id=lead.id, subject="Hi", body="Hello", type="outreach")
    db_session.add(email)
    await db_session.flush()

    email_id = email.id
    await db_session.delete(lead)
    await db_session.flush()

    result = await db_session.execute(select(Email).where(Email.id == email_id))
    assert result.scalar_one_or_none() is None
