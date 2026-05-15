"""Personalization Agent — Phase 3B.

Public entry point: `run_personalization_agent(lead, research, campaign_context) -> dict`.

A 4-node LangGraph workflow that retrieves email templates from Qdrant, drafts a
personalized cold email with Claude (tool_use), enforces compliance with GPT-4o-mini
for semantic checks (unverifiable claims, opening_line overlap), refines up to 2 times,
and raises AgentOutputError if compliance still fails.

Compliance checks:
  Deterministic (no LLM): spam trigger words, body word count, subject length.
  Semantic (GPT-4o-mini): unverifiable claims, opening_line research overlap.
"""
from __future__ import annotations

import json
import logging
from typing import Any, TypedDict

import anthropic
import openai
from langgraph.graph import END, START, StateGraph
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from agents.prompts.personalization_prompts import (
    COMPLIANCE_SYSTEM,
    DRAFT_SYSTEM,
    REFINE_SYSTEM,
)
from core.vector_store import get_vector_store

logger = logging.getLogger(__name__)

SPAM_WORDS = {
    "guaranteed",
    "free money",
    "act now",
    "limited time",
    "click here",
    "100%",
    "unlimited",
    "best price",
    "risk-free",
    "winner",
    "congratulations",
}

EMAIL_DRAFT_TOOL = {
    "name": "submit_draft",
    "description": "Submit the drafted cold email.",
    "input_schema": {
        "type": "object",
        "properties": {
            "subject": {"type": "string"},
            "opening_line": {"type": "string"},
            "body": {"type": "string"},
            "cta": {"type": "string"},
            "full_email": {"type": "string"},
        },
        "required": ["subject", "opening_line", "body", "cta", "full_email"],
    },
}


class PersonalizationState(TypedDict):
    lead: dict[str, Any]
    research: dict[str, Any]
    campaign_context: dict[str, Any]
    templates: list[dict[str, Any]]
    draft: dict[str, Any] | None
    compliance_violations: list[str]
    refine_count: int


def _build_draft_user_message(
    lead: dict,
    research: dict,
    campaign_context: dict,
    templates: list[dict],
    violations: list[str] | None,
) -> str:
    parts = [
        f"Company: {lead.get('company_name', '')}",
        f"Contact: {lead.get('contact_name', '')}",
        f"Email: {lead.get('email', '')}",
        "",
        "RESEARCH:",
        f"Industry: {research.get('industry', '')}",
        f"Pain points: {', '.join(research.get('pain_points', []))}",
        f"Recent news: {', '.join(research.get('recent_news', []))}",
        f"Research summary: {research.get('research_summary', '')}",
        "",
        "CAMPAIGN CONTEXT:",
        f"Product: {campaign_context.get('product', '')}",
        f"Value prop: {campaign_context.get('value_prop', '')}",
        f"Case study: {campaign_context.get('case_study', '')}",
        f"Tone: {campaign_context.get('tone', 'direct')}",
    ]
    if templates:
        parts.append("")
        parts.append("EXAMPLE TEMPLATES (style reference only — do not copy):")
        for t in templates[:2]:
            parts.append(f"- {t.get('email_body', '')[:200]}")
    if violations:
        parts.append("")
        parts.append("VIOLATIONS TO FIX IN THIS REVISION:")
        for v in violations:
            parts.append(f"- {v}")
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
async def _call_claude_draft(
    lead: dict[str, Any],
    research: dict[str, Any],
    campaign_context: dict[str, Any],
    templates: list[dict[str, Any]],
    violations: list[str] | None = None,
) -> dict[str, Any]:
    from core.config import settings

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    system = REFINE_SYSTEM if violations else DRAFT_SYSTEM
    user_message = _build_draft_user_message(lead, research, campaign_context, templates, violations)

    resp = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system,
        tools=[EMAIL_DRAFT_TOOL],
        tool_choice={"type": "tool", "name": "submit_draft"},
        messages=[{"role": "user", "content": user_message}],
    )
    tool_use = next(b for b in resp.content if getattr(b, "type", None) == "tool_use")
    return tool_use.input


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
async def _call_openai_compliance(
    draft: dict[str, Any],
    research_summary: str,
) -> dict[str, Any]:
    from core.config import settings

    client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    user_content = (
        f"Opening line: {draft.get('opening_line', '')}\n"
        f"Body: {draft.get('body', '')}\n\n"
        f"Research summary: {research_summary}\n\n"
        'Return JSON: {"violations": ["...", ...]} or {"violations": []} if clean.'
    )
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": COMPLIANCE_SYSTEM},
            {"role": "user", "content": user_content},
        ],
    )
    return json.loads(resp.choices[0].message.content)


async def retrieve_templates(state: PersonalizationState) -> dict[str, Any]:
    try:
        vs = get_vector_store()
        industry = state["research"].get("industry", "")
        pain_point = (state["research"].get("pain_points") or [""])[0]
        templates = await vs.get_best_templates(industry, pain_point)
        return {"templates": templates}
    except Exception as e:
        logger.warning("Template retrieval failed — continuing without templates: %s", e)
        return {"templates": []}


async def draft_email(state: PersonalizationState) -> dict[str, Any]:
    result = await _call_claude_draft(
        state["lead"],
        state["research"],
        state["campaign_context"],
        state["templates"],
    )
    return {"draft": result}


async def compliance_check(state: PersonalizationState) -> dict[str, Any]:
    draft = state["draft"] or {}
    violations: list[str] = []

    # (a) Spam trigger words — deterministic substring search
    body_lower = draft.get("body", "").lower()
    for word in SPAM_WORDS:
        if word in body_lower:
            violations.append(f"spam trigger word: '{word}'")

    # (c) Body word count — deterministic
    if len(draft.get("body", "").split()) > 200:
        violations.append("body too long (over 200 words)")

    # (e) Subject length — deterministic
    subject = draft.get("subject", "")
    if len(subject) > 60:
        violations.append(f"subject too long ({len(subject)} chars)")

    # Short-circuit: skip LLM if deterministic violations already found
    if violations:
        return {"compliance_violations": violations}

    # (b) Unverifiable claims + (d) Opening line overlap — semantic via GPT-4o-mini
    result = await _call_openai_compliance(
        draft,
        state["research"].get("research_summary", ""),
    )
    return {"compliance_violations": result.get("violations", [])}


async def refine(state: PersonalizationState) -> dict[str, Any]:
    result = await _call_claude_draft(
        state["lead"],
        state["research"],
        state["campaign_context"],
        state["templates"],
        violations=state["compliance_violations"],
    )
    return {"draft": result, "refine_count": state["refine_count"] + 1}


def _route_after_compliance(state: PersonalizationState) -> str:
    if not state["compliance_violations"] or state["refine_count"] >= 2:
        return "end"
    return "refine"


def _build_graph():
    graph = StateGraph(PersonalizationState)
    graph.add_node("retrieve_templates", retrieve_templates)
    graph.add_node("draft_email", draft_email)
    graph.add_node("compliance_check", compliance_check)
    graph.add_node("refine", refine)

    graph.add_edge(START, "retrieve_templates")
    graph.add_edge("retrieve_templates", "draft_email")
    graph.add_edge("draft_email", "compliance_check")
    graph.add_conditional_edges(
        "compliance_check",
        _route_after_compliance,
        {"end": END, "refine": "refine"},
    )
    graph.add_edge("refine", "compliance_check")
    return graph.compile()


_graph = _build_graph()


async def run_personalization_agent(
    lead: dict[str, Any],
    research: dict[str, Any],
    campaign_context: dict[str, Any],
) -> dict[str, Any]:
    """Entry point — runs the compiled LangGraph personalization pipeline."""
    from core.exceptions import AgentOutputError

    initial: PersonalizationState = {
        "lead": lead,
        "research": research,
        "campaign_context": campaign_context,
        "templates": [],
        "draft": None,
        "compliance_violations": [],
        "refine_count": 0,
    }
    final = await _graph.ainvoke(initial)

    if final["compliance_violations"]:
        raise AgentOutputError(
            agent="personalization",
            violations=final["compliance_violations"],
        )

    return final["draft"]
