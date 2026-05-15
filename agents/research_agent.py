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
import json
import logging
import re
from typing import Any, TypedDict

import anthropic
import httpx
import openai
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from tavily import AsyncTavilyClient
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from agents.prompts.research_prompts import QUALITY_CHECK_SYSTEM, SYNTHESIS_SYSTEM

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


RESEARCH_OUTPUT_TOOL = {
    "name": "submit_research",
    "description": "Submit the structured research findings.",
    "input_schema": {
        "type": "object",
        "properties": {
            "industry": {"type": "string"},
            "company_size": {"type": "string"},
            "pain_points": {"type": "array", "items": {"type": "string"},
                            "minItems": 2, "maxItems": 4},
            "recent_news": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
            "tech_stack": {"type": "array", "items": {"type": "string"}},
            "research_summary": {"type": "string"},
        },
        "required": ["industry", "company_size", "pain_points",
                     "recent_news", "tech_stack", "research_summary"],
    },
}


def _build_synthesize_user_message(state: ResearchState, refine_context: dict | None) -> str:
    parts: list[str] = [
        f"Company: {state['lead']['company_name']}",
        f"Website: {state['lead']['website']}",
        "",
        "WEBSITE TEXT (truncated):",
        state.get("raw_website_text") or "<no website content available>",
        "",
        "RECENT NEWS:",
    ]
    if state.get("news_results"):
        for item in state["news_results"][:5]:
            parts.append(f"- {item.get('title', '')}: {item.get('content', '')}")
    else:
        parts.append("<no news results>")
    parts.append("")
    parts.append(f"TECH_STACK_HINTS: {state.get('tech_stack_hints', [])}")

    if refine_context:
        parts.append("")
        parts.append("REFINEMENT NOTE:")
        parts.append(refine_context["instruction"])
        parts.append(f"PRIOR SUMMARY (rejected): {refine_context['prior_summary']}")

    return "\n".join(parts)


@retry(
    retry=retry_if_exception_type((
        anthropic.APIConnectionError,
        anthropic.RateLimitError,
        anthropic.APITimeoutError,
    )),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
async def _call_claude_synthesize(user_message: str, refine_context: dict | None = None) -> dict[str, Any]:
    from core.config import settings
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    resp = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=SYNTHESIS_SYSTEM,
        tools=[RESEARCH_OUTPUT_TOOL],
        tool_choice={"type": "tool", "name": "submit_research"},
        messages=[{"role": "user", "content": user_message}],
    )
    tool_use = next(b for b in resp.content if getattr(b, "type", None) == "tool_use")
    return tool_use.input


async def synthesize(state: ResearchState) -> dict[str, Any]:
    refine_count = state["refine_count"]
    refine_context = None
    if not state["quality_ok"] and state["synthesized"] is not None:
        refine_count += 1
        refine_context = {
            "prior_summary": state["synthesized"].get("research_summary", ""),
            "instruction": (
                "Previous attempt failed the quality check. Write a more specific "
                "summary that references a concrete fact from the source material."
            ),
        }
    user_message = _build_synthesize_user_message(state, refine_context)
    raw_output = await _call_claude_synthesize(user_message, refine_context=refine_context)
    return {"synthesized": raw_output, "refine_count": refine_count}


@retry(
    retry=retry_if_exception_type((
        openai.APIConnectionError,
        openai.RateLimitError,
        openai.APITimeoutError,
    )),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
async def _call_openai_quality(summary: str) -> dict[str, Any]:
    from core.config import settings
    client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": QUALITY_CHECK_SYSTEM},
            {"role": "user", "content": f"Summary:\n{summary}\n\nReturn JSON {{\"passes\": bool, \"reason\": str}}."},
        ],
    )
    return json.loads(resp.choices[0].message.content)


async def check_quality(state: ResearchState) -> dict[str, Any]:
    summary = (state["synthesized"] or {}).get("research_summary", "")
    if len(summary.split()) < 20:
        return {"quality_ok": False}

    result = await _call_openai_quality(summary)
    return {"quality_ok": bool(result.get("passes"))}


async def run_research_agent(lead: dict[str, Any]) -> dict[str, Any]:
    """Entry point — implemented progressively across Tasks 6–11."""
    raise NotImplementedError("filled in by later tasks")
