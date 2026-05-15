"""Backend interface for the Research Agent.

This is the only place backend code touches the Research Agent. The agent itself
lives in `agents/research_agent.py` and stays free of DB and HTTP concerns.
"""
import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from agents.research_agent import run_research_agent
from core.vector_store import get_vector_store
from models.lead import Lead

logger = logging.getLogger(__name__)


async def trigger_research(lead_id: UUID, db: AsyncSession) -> dict[str, Any]:
    lead = await db.get(Lead, lead_id)
    if lead is None:
        raise LookupError(f"Lead {lead_id} not found")

    result = await run_research_agent({
        "company_name": lead.company_name,
        "website": lead.website,
    })

    lead.research_data = result
    lead.status = "researched"
    await db.commit()

    # Vector upsert is best-effort — DB write is the source of truth.
    try:
        vs = get_vector_store()
        await vs.upsert_company_research(lead_id, result["research_summary"], result)
    except Exception as e:
        logger.warning("Vector upsert failed for lead %s: %s", lead_id, e)

    return result
