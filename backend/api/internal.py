import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from agents_interface.followup import trigger_followup as trigger_followup_iface
from agents_interface.personalization import trigger_personalization as trigger_personalization_iface
from agents_interface.research import trigger_research as trigger_research_iface
from core.config import settings
from core.database import get_db
from core.response import ok

router = APIRouter(prefix="/internal", tags=["internal"])
logger = logging.getLogger(__name__)


async def _require_token(x_internal_token: str = Header(default=None)) -> None:
    if x_internal_token != settings.internal_api_token:
        raise HTTPException(
            status_code=401,
            detail={
                "data": None,
                "error": {"code": "UNAUTHORIZED", "message": "Invalid or missing X-Internal-Token"},
                "meta": {},
            },
        )


class LeadTriggerBody(BaseModel):
    lead_id: UUID


@router.post("/trigger-research", dependencies=[Depends(_require_token)])
async def trigger_research(body: LeadTriggerBody, db: AsyncSession = Depends(get_db)):
    try:
        result = await trigger_research_iface(body.lead_id, db)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ok(result)


@router.post("/trigger-personalization", dependencies=[Depends(_require_token)])
async def trigger_personalization(body: LeadTriggerBody, db: AsyncSession = Depends(get_db)):
    try:
        result = await trigger_personalization_iface(body.lead_id, db)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ok(result)


@router.post("/trigger-followup", dependencies=[Depends(_require_token)])
async def trigger_followup(body: LeadTriggerBody, db: AsyncSession = Depends(get_db)):
    try:
        result = await trigger_followup_iface(body.lead_id, db)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ok(result)


@router.get("/leads-needing-followup", dependencies=[Depends(_require_token)])
async def leads_needing_followup(db: AsyncSession = Depends(get_db)):
    stmt = text(
        """
        SELECT
            l.id::text AS lead_id,
            ROUND(EXTRACT(EPOCH FROM (NOW() - MAX(e.sent_at))) / 86400.0, 2) AS days_since_sent
        FROM leads l
        JOIN emails e ON e.lead_id = l.id
        WHERE l.status = 'email_sent'
        AND NOT EXISTS (
            SELECT 1 FROM replies r
            JOIN emails e2 ON e2.id = r.email_id
            WHERE e2.lead_id = l.id
        )
        GROUP BY l.id
        HAVING
            (EXTRACT(EPOCH FROM (NOW() - MAX(e.sent_at))) / 3600.0 BETWEEN 60 AND 84)
            OR (EXTRACT(EPOCH FROM (NOW() - MAX(e.sent_at))) / 3600.0 BETWEEN 156 AND 180)
            OR (EXTRACT(EPOCH FROM (NOW() - MAX(e.sent_at))) / 3600.0 BETWEEN 324 AND 348)
        """
    )
    rows = (await db.execute(stmt)).all()
    return ok([{"lead_id": row.lead_id, "days_since_sent": float(row.days_since_sent)} for row in rows])
