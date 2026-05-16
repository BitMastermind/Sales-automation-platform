"""Backend interface for the Follow-up Agent.

This is the only place backend code touches the Follow-up Agent. The agent
lives in `agents/followup_agent.py` and stays free of DB and HTTP concerns.
"""
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.followup_agent import FollowupResult, run_followup_agent
from models.email import Email
from models.lead import Lead

logger = logging.getLogger(__name__)


async def trigger_followup(lead_id: UUID, db: AsyncSession) -> dict[str, Any]:
    lead = await db.get(Lead, lead_id)
    if lead is None:
        raise LookupError(f"Lead {lead_id} not found")

    stmt = (
        select(Email)
        .where(Email.lead_id == lead_id)
        .order_by(Email.sent_at.asc())
    )
    emails = list((await db.execute(stmt)).scalars().all())
    if not emails:
        raise LookupError(f"No emails found for lead {lead_id}")

    from datetime import datetime, timezone
    latest = max(e for e in emails if e.sent_at is not None)
    days_elapsed = (datetime.now(timezone.utc) - latest.sent_at).days

    original = next((e for e in emails if e.type == "outreach"), emails[0])
    original_email = {"subject": original.subject or "", "body": original.body or ""}

    prior_followups = [
        {"type": e.type, "body": e.body or ""}
        for e in emails
        if e.type == "followup"
    ]

    result: FollowupResult = await run_followup_agent(
        lead_id=str(lead_id),
        days_since_last_touch=days_elapsed,
        original_email=original_email,
        prior_followups=prior_followups,
        research=lead.research_data or {},
    )

    if result.should_send:
        email = Email(
            lead_id=lead_id,
            subject=result.subject,
            body=result.body,
            type="followup",
        )
        db.add(email)
        await db.commit()
        logger.info("Follow-up email queued for lead %s (strategy=%s)", lead_id, result.strategy)

    return result.model_dump()
