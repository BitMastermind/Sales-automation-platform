"""Backend interface for the Reply Classifier.

The agent lives in `agents/reply_classifier.py` and stays free of DB concerns;
this module is the only place backend code touches it.
"""
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from agents.reply_classifier import ClassificationResult, run_reply_classifier
from models.email import Email
from models.lead import Lead
from models.reply import Reply

logger = logging.getLogger(__name__)


async def classify_reply(reply_id: UUID, db: AsyncSession) -> ClassificationResult:
    reply = await db.get(Reply, reply_id)
    if reply is None:
        raise LookupError(f"Reply {reply_id} not found")

    email = await db.get(Email, reply.email_id)
    if email is None:
        raise LookupError(f"Email {reply.email_id} not found for reply {reply_id}")

    result = await run_reply_classifier(reply.content, prior_email=email.body)

    reply.classified_as = result.intent

    if result.intent in ("interested", "meeting_request"):
        lead = await db.get(Lead, email.lead_id)
        if lead is not None:
            lead.status = "meeting_booked"
    elif result.intent == "unsubscribe":
        lead = await db.get(Lead, email.lead_id)
        if lead is not None:
            lead.status = "unsubscribed"

    await db.flush()
    return result
