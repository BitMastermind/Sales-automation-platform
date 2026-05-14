from typing import Any


async def run_research_agent(lead: dict[str, Any]) -> dict[str, Any]:
    """Research a company and return structured research data.

    Args:
        lead: Dict with at minimum 'company_name' and 'website'.

    Returns:
        Structured research dict matching ResearchOutput schema (see docs/03-AGENTS.md).
    """
    raise NotImplementedError
