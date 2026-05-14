import asyncio
import logging
from typing import Literal
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import case, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.response import err, ok, paginated
from models.campaign import Campaign
from models.email import Email
from models.lead import Lead
from schemas.campaign import CampaignCreate, CampaignRead

router = APIRouter(prefix="/campaigns", tags=["campaigns"])
logger = logging.getLogger(__name__)


class StatusUpdate(BaseModel):
    status: Literal["active", "paused", "completed"]


def _stats_stmt():
    """Single query: campaigns + aggregated lead/email stats. No N+1."""
    return (
        select(
            Campaign,
            func.count(distinct(Lead.id)).label("leads_count"),
            func.count(distinct(case((Email.sent_at.isnot(None), Email.id)))).label("emails_sent"),
            func.count(distinct(case((Email.opened_at.isnot(None), Email.id)))).label("emails_opened"),
            func.count(distinct(case((Email.replied_at.isnot(None), Email.id)))).label("emails_replied"),
            func.count(distinct(case((Lead.status == "meeting_booked", Lead.id)))).label(
                "meetings_booked"
            ),
        )
        .outerjoin(Lead, Lead.campaign_id == Campaign.id)
        .outerjoin(Email, Email.lead_id == Lead.id)
        .group_by(Campaign.id)
    )


def _stats_dict(row) -> dict:
    _, leads_count, emails_sent, emails_opened, emails_replied, meetings_booked = row
    return {
        "leads_count": leads_count,
        "emails_sent": emails_sent,
        "open_rate": round(emails_opened / emails_sent, 4) if emails_sent else 0.0,
        "reply_rate": round(emails_replied / emails_sent, 4) if emails_sent else 0.0,
        "meetings_booked": meetings_booked,
    }


@router.post("", status_code=201)
async def create_campaign(body: CampaignCreate, db: AsyncSession = Depends(get_db)):
    campaign = Campaign(**body.model_dump())
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return ok(CampaignRead.model_validate(campaign).model_dump())


@router.get("")
async def list_campaigns(page: int = 1, size: int = 20, db: AsyncSession = Depends(get_db)):
    total = (await db.scalar(select(func.count()).select_from(Campaign))) or 0
    stmt = (
        _stats_stmt()
        .order_by(Campaign.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    rows = (await db.execute(stmt)).all()
    data = []
    for row in rows:
        item = CampaignRead.model_validate(row[0]).model_dump()
        item["stats"] = _stats_dict(row)
        data.append(item)
    return paginated(data, page, size, total)


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: UUID, db: AsyncSession = Depends(get_db)):
    stmt = _stats_stmt().where(Campaign.id == campaign_id)
    row = (await db.execute(stmt)).one_or_none()
    if row is None:
        err("CAMPAIGN_NOT_FOUND", "Campaign not found", 404)
    item = CampaignRead.model_validate(row[0]).model_dump()
    item["stats"] = _stats_dict(row)
    return ok(item)


async def _fire_n8n_campaign_launch(campaign_id: str) -> None:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{settings.n8n_webhook_url}/campaign-launcher",
                json={"campaign_id": campaign_id},
            )
    except Exception:
        logger.error("n8n launch notification failed for campaign %s", campaign_id, exc_info=True)


@router.patch("/{campaign_id}/status")
async def patch_campaign_status(
    campaign_id: UUID, body: StatusUpdate, db: AsyncSession = Depends(get_db)
):
    campaign = await db.get(Campaign, campaign_id)
    if campaign is None:
        err("CAMPAIGN_NOT_FOUND", "Campaign not found", 404)
    campaign.status = body.status
    await db.commit()
    await db.refresh(campaign)
    if body.status == "active":
        asyncio.create_task(_fire_n8n_campaign_launch(str(campaign_id)))
    return ok(CampaignRead.model_validate(campaign).model_dump())
