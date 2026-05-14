from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


async def run_followup_agent(
    lead_id: str,
    db_session: AsyncSession,
) -> dict[str, Any]:
    """Generate a follow-up email or signal should_send=false.

    Returns:
        Dict with keys: should_send, subject, body, strategy.
    """
    raise NotImplementedError
