from typing import Any


async def run_personalization_agent(
    lead: dict[str, Any],
    research: dict[str, Any],
    campaign_context: dict[str, Any],
) -> dict[str, Any]:
    """Generate a personalized outreach email.

    Returns:
        Dict with keys: subject, opening_line, body, cta, full_email.
    """
    raise NotImplementedError
