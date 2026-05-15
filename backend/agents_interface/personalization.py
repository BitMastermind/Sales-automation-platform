"""Backend interface for the Personalization Agent.

This is the only place backend code touches the Personalization Agent. The agent
lives in `agents/personalization_agent.py` and stays free of DB and HTTP concerns.
"""
import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from agents.personalization_agent import run_personalization_agent
from models.email import Email
from models.lead import Lead

logger = logging.getLogger(__name__)


async def trigger_personalization(lead_id: UUID, db: AsyncSession) -> dict[str, Any]:
    lead = await db.get(Lead, lead_id)
    if lead is None:
        raise LookupError(f"Lead {lead_id} not found")

    if lead.research_data is None:
        raise ValueError("Lead must be researched first")

    from models.campaign import Campaign
    campaign = await db.get(Campaign, lead.campaign_id)
    campaign_context = campaign.settings or {} if campaign else {}

    result = await run_personalization_agent(
        lead={
            "company_name": lead.company_name,
            "website": lead.website or "",
            "contact_name": lead.contact_name or "",
            "email": lead.email,
        },
        research=lead.research_data,
        campaign_context=campaign_context,
    )

    email = Email(
        lead_id=lead_id,
        subject=result["subject"],
        body=result["full_email"],
        type="outreach",
    )
    db.add(email)
    await db.commit()

    return result
