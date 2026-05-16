"""Backend interface for the Follow-up Agent."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.followup_agent import FollowupResult, run_followup_agent
from models.email import Email
from models.lead import Lead

logger = logging.getLogger(__name__)


async def trigger_followup(lead_id: UUID, db: AsyncSession) -> FollowupResult:
    lead = await db.get(Lead, lead_id)
    if lead is None:
        raise LookupError(f"Lead {lead_id} not found")

    stmt = select(Email).where(Email.lead_id == lead_id).order_by(Email.sent_at)
    rows = (await db.execute(stmt)).scalars().all()
    if not rows:
        raise ValueError(f"Lead {lead_id} has no sent emails")

    most_recent = max(rows, key=lambda e: e.sent_at or datetime.min.replace(tzinfo=timezone.utc))
    sent_at = most_recent.sent_at
    if sent_at is None:
        raise ValueError(f"Lead {lead_id} most recent email has no sent_at")

    now = datetime.now(tz=timezone.utc)
    if sent_at.tzinfo is None:
        sent_at = sent_at.replace(tzinfo=timezone.utc)
    days_elapsed = int((now - sent_at).total_seconds() / 86400)

    original_email_row = next((e for e in rows if e.type != "followup"), most_recent)
    original_email = {"subject": original_email_row.subject, "body": original_email_row.body}

    prior_followups = [
        {"type": "followup", "body": e.body}
        for e in rows
        if e.type == "followup"
    ]

    research = lead.research_data or {}

    result = await run_followup_agent(
        lead_id=str(lead_id),
        days_since_last_touch=days_elapsed,
        original_email=original_email,
        prior_followups=prior_followups,
        research=research,
    )

    if result.should_send:
        new_email = Email(
            lead_id=lead_id,
            subject=result.subject,
            body=result.body,
            type="followup",
        )
        db.add(new_email)
        await db.commit()
        logger.info("Follow-up email queued for lead %s (strategy=%s)", lead_id, result.strategy)

    return result
