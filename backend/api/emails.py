import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.response import err, ok
from models.email import Email
from schemas.email import EmailRead

router = APIRouter(prefix="/emails", tags=["emails"])
logger = logging.getLogger(__name__)


@router.get("")
async def list_emails(lead_id: UUID | None = None, db: AsyncSession = Depends(get_db)):
    stmt = select(Email).order_by(Email.sent_at.desc())
    if lead_id is not None:
        stmt = stmt.where(Email.lead_id == lead_id)
    emails = (await db.execute(stmt)).scalars().all()
    return ok([EmailRead.model_validate(e).model_dump() for e in emails])


@router.post("/{email_id}/resend")
async def resend_email(email_id: UUID, db: AsyncSession = Depends(get_db)):
    email = await db.get(Email, email_id)
    if email is None:
        err("EMAIL_NOT_FOUND", "Email not found", 404)

    import asyncio

    async def _trigger() -> None:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{settings.next_public_api_base}/api/internal/trigger-personalization",
                    json={"lead_id": str(email.lead_id)},
                    headers={"X-Internal-Token": settings.internal_api_token},
                )
        except Exception:
            logger.error(
                "trigger-personalization failed for lead %s", email.lead_id, exc_info=True
            )

    asyncio.create_task(_trigger())
    return ok({"queued": True})
