"""Research Agent — Phase 3A.

Public entry point: `run_research_agent(lead) -> dict`.

A 5-node LangGraph workflow that fetches a company's website, retrieves news
from Tavily, synthesizes a structured research dict with Claude, validates
quality with GPT-4o-mini, and refines up to 2 times.

Pydantic validation lives at the entry point (after the graph), keeping schema
errors separate from quality failures.
"""
from __future__ import annotations

from typing import Any, TypedDict

from pydantic import BaseModel, Field


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


async def run_research_agent(lead: dict[str, Any]) -> dict[str, Any]:
    """Entry point — implemented progressively across Tasks 6–11."""
    raise NotImplementedError("filled in by later tasks")
