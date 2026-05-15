"""Research Agent — Phase 3A.

Public entry point: `run_research_agent(lead) -> dict`.

A 5-node LangGraph workflow that fetches a company's website, retrieves news
from Tavily, synthesizes a structured research dict with Claude, validates
quality with GPT-4o-mini, and refines up to 2 times.

Pydantic validation lives at the entry point (after the graph), keeping schema
errors separate from quality failures.
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, TypedDict

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from tavily import AsyncTavilyClient

logger = logging.getLogger(__name__)


class ResearchState(TypedDict):
    lead: dict[str, Any]                    # {"company_name": str, "website": str}
    raw_website_text: str | None            # "" on fetch failure (graceful degradation)
    news_results: list[dict[str, Any]]      # [] on Tavily failure
    tech_stack_hints: list[str]
    synthesized: dict[str, Any] | None      # raw tool_use input (validated at entry point)
    quality_ok: bool                        # set by check_quality
    refine_count: int                       # 0, 1, or 2 — incremented in synthesize on re-entry


class ResearchOutput(BaseModel):
    industry: str
    company_size: str
    pain_points: list[str] = Field(min_length=2, max_length=4)
    recent_news: list[str] = Field(max_length=3)
    tech_stack: list[str]
    research_summary: str


TECH_KEYWORDS = [
    "Salesforce", "HubSpot", "Outreach", "Gong", "Slack",
    "Notion", "Jira", "AWS", "GCP", "Azure",
]


async def extract_tech_stack(state: ResearchState) -> dict[str, Any]:
    haystack_parts = [state.get("raw_website_text") or ""]
    for item in state.get("news_results", []):
        haystack_parts.append(item.get("content", ""))
    haystack = " ".join(haystack_parts).lower()

    hits: list[str] = []
    for kw in TECH_KEYWORDS:
        if re.search(rf"\b{re.escape(kw.lower())}\b", haystack):
            hits.append(kw)
    return {"tech_stack_hints": hits}


def _extract_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    parts: list[str] = []

    desc = soup.find("meta", attrs={"name": "description"})
    if desc and desc.get("content"):
        parts.append(desc["content"].strip())

    for tag_name in ("h1", "h2", "h3", "p"):
        for el in soup.find_all(tag_name):
            text = el.get_text(strip=True)
            if text:
                parts.append(text)

    return "\n".join(parts).strip()


async def fetch_website(state: ResearchState) -> dict[str, Any]:
    url = state["lead"]["website"]
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "SalesAutomationBot/1.0"})
            resp.raise_for_status()
        text = await asyncio.to_thread(_extract_text, resp.text)
        return {"raw_website_text": text[:3000]}
    except Exception as e:
        logger.warning("fetch_website failed for %s: %s", url, e)
        return {"raw_website_text": ""}


async def search_news(state: ResearchState) -> dict[str, Any]:
    from core.config import settings  # local import — keeps agents loadable without backend on path
    client = AsyncTavilyClient(api_key=settings.tavily_api_key)
    try:
        query = f"{state['lead']['company_name']} company news 2024 2025"
        results = await client.search(query, max_results=5)
        return {"news_results": results.get("results", [])}
    except Exception as e:
        logger.warning("Tavily search failed: %s", e)
        return {"news_results": []}


async def run_research_agent(lead: dict[str, Any]) -> dict[str, Any]:
    """Entry point — implemented progressively across Tasks 6–11."""
    raise NotImplementedError("filled in by later tasks")
