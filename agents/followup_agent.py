"""Follow-up Agent — Phase 3D.

Public entry point:
    run_followup_agent(lead_id, days_since_last_touch, original_email,
                       prior_followups, research) -> FollowupResult

A 2-node LangGraph conditional graph:
  START → select_strategy → END                   (strategy == "stop")
  START → select_strategy → generate_followup → END

select_strategy is deterministic (no LLM). generate_followup calls Claude
with a strategy-specific system prompt. If the same strategy appears in
prior_followups, the system prompt is modified to avoid repeating the angle.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Literal, TypedDict

import anthropic
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from agents.prompts.followup_prompts import (
    DAY_14_BREAKUP_SYSTEM,
    DAY_3_BUMP_SYSTEM,
    DAY_7_VALUE_ADD_SYSTEM,
)

logger = logging.getLogger(__name__)

_STRATEGY_SYSTEM: dict[str, str] = {
    "day_3_bump": DAY_3_BUMP_SYSTEM,
    "day_7_value_add": DAY_7_VALUE_ADD_SYSTEM,
    "day_14_breakup": DAY_14_BREAKUP_SYSTEM,
}

_FOLLOWUP_TOOL = {
    "name": "submit_followup",
    "description": "Submit the follow-up email.",
    "input_schema": {
        "type": "object",
        "properties": {
            "subject": {"type": "string"},
            "body": {"type": "string"},
        },
        "required": ["subject", "body"],
    },
}


class FollowupResult(BaseModel):
    should_send: bool
    subject: str | None = None
    body: str | None = None
    strategy: Literal["day_3_bump", "day_7_value_add", "day_14_breakup", "stop"] | None = None


class FollowupState(TypedDict):
    lead_id: str
    days_since_last_touch: int
    original_email: dict[str, Any]
    prior_followups: list[dict[str, Any]]
    research: dict[str, Any]
    strategy: str | None
    should_send: bool
    subject: str | None
    body: str | None


@retry(
    retry=retry_if_exception_type((
        anthropic.APIConnectionError,
        anthropic.RateLimitError,
        anthropic.APITimeoutError,
    )),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
)
async def _call_claude_generate(user_message: str, system_prompt: str) -> dict[str, str]:
    client = anthropic.AsyncAnthropic()
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        system=system_prompt,
        tools=[_FOLLOWUP_TOOL],
        tool_choice={"type": "tool", "name": "submit_followup"},
        messages=[{"role": "user", "content": user_message}],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_followup":
            return block.input
    raise ValueError("Claude did not call submit_followup tool")


def _select_strategy(state: FollowupState) -> dict[str, Any]:
    days = state["days_since_last_touch"]
    if days > 14:
        return {"strategy": "stop", "should_send": False}
    if days >= 14:
        strategy = "day_14_breakup"
    elif days >= 7:
        strategy = "day_7_value_add"
    else:
        strategy = "day_3_bump"
    return {"strategy": strategy, "should_send": True}


async def _generate_followup(state: FollowupState) -> dict[str, Any]:
    strategy = state["strategy"]
    system_prompt = _STRATEGY_SYSTEM[strategy]

    prior_strategies = [p.get("type") for p in state["prior_followups"]]
    if strategy in prior_strategies:
        system_prompt = system_prompt + "\n\nAdjust the angle slightly — the recipient has already seen this type of follow-up."

    user_message = "\n".join([
        f"Original email subject: {state['original_email'].get('subject', '')}",
        f"Original email body: {state['original_email'].get('body', '')}",
        "",
        f"Research summary: {state['research'].get('research_summary', '')}",
        f"Pain points: {', '.join(state['research'].get('pain_points', []))}",
        "",
        "Prior follow-ups sent:",
        *[f"- [{p.get('type')}] {p.get('body', '')[:100]}" for p in state["prior_followups"]],
    ])

    output = await _call_claude_generate(user_message, system_prompt)
    return {"subject": output.get("subject"), "body": output.get("body")}


def _route_after_strategy(state: FollowupState) -> str:
    return "end" if state["strategy"] == "stop" else "generate"


_graph_builder = StateGraph(FollowupState)
_graph_builder.add_node("select_strategy", _select_strategy)
_graph_builder.add_node("generate_followup", _generate_followup)
_graph_builder.add_edge(START, "select_strategy")
_graph_builder.add_conditional_edges(
    "select_strategy",
    _route_after_strategy,
    {"end": END, "generate": "generate_followup"},
)
_graph_builder.add_edge("generate_followup", END)
_graph = _graph_builder.compile()


async def run_followup_agent(
    lead_id: str,
    days_since_last_touch: int,
    original_email: dict[str, Any],
    prior_followups: list[dict[str, Any]],
    research: dict[str, Any],
) -> FollowupResult:
    initial: FollowupState = {
        "lead_id": lead_id,
        "days_since_last_touch": days_since_last_touch,
        "original_email": original_email,
        "prior_followups": prior_followups,
        "research": research,
        "strategy": None,
        "should_send": False,
        "subject": None,
        "body": None,
    }
    final = await _graph.ainvoke(initial)
    return FollowupResult(
        should_send=final["should_send"],
        subject=final.get("subject"),
        body=final.get("body"),
        strategy=final["strategy"],
    )
