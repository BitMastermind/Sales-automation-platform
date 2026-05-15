import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agents_interface.classifier import classify_reply
from core.database import get_db
from core.response import err, ok
from models.email import Email
from models.lead import Lead
from models.reply import Reply

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)


class ReplyReceivedBody(BaseModel):
    gmail_message_id: str
    reply_text: str
    received_at: datetime


class EmailOpenedBody(BaseModel):
    email_id: UUID
    opened_at: datetime


@router.post("/n8n/reply-received")
async def reply_received(body: ReplyReceivedBody, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Email).where(Email.gmail_message_id == body.gmail_message_id)
    )
    email = result.scalar_one_or_none()
    if email is None:
        err("EMAIL_NOT_FOUND", "No email found for that gmail_message_id", 404)

    reply = Reply(
        email_id=email.id,
        content=body.reply_text,
        received_at=body.received_at,
    )
    db.add(reply)
    await db.flush()

    email.replied_at = datetime.now(timezone.utc)
    lead = await db.get(Lead, email.lead_id)
    if lead is not None:
        lead.status = "replied"

    classification = await classify_reply(reply.id, db)
    await db.commit()

    return ok({"reply_id": str(reply.id), "classified_as": classification.intent})


@router.post("/n8n/email-opened")
async def email_opened(body: EmailOpenedBody, db: AsyncSession = Depends(get_db)):
    email = await db.get(Email, body.email_id)
    if email is None:
        err("EMAIL_NOT_FOUND", "Email not found", 404)
    await db.execute(
        update(Email).where(Email.id == body.email_id).values(opened_at=body.opened_at)
    )
    await db.commit()
    return ok({"email_id": str(body.email_id), "opened_at": body.opened_at.isoformat()})
