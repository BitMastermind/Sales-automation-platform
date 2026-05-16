"""Follow-up Agent — Phase 3D.

Public entry point: `run_followup_agent(lead_id, days_since_last_touch, original_email,
                                        prior_followups, research) -> FollowupResult`.

A 2-node LangGraph conditional graph:
  START → select_strategy → END                   (strategy == "stop")
                          → generate_followup → END
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


FOLLOWUP_OUTPUT_TOOL = {
    "name": "submit_followup_email",
    "description": "Submit the generated follow-up email.",
    "input_schema": {
        "type": "object",
        "properties": {
            "subject": {"type": "string"},
            "body": {"type": "string"},
        },
        "required": ["subject", "body"],
    },
}


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
async def _call_claude_generate(system_prompt: str, user_message: str) -> dict[str, Any]:
    from core.config import settings
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    resp = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=system_prompt,
        tools=[FOLLOWUP_OUTPUT_TOOL],
        tool_choice={"type": "tool", "name": "submit_followup_email"},
        messages=[{"role": "user", "content": user_message}],
    )
    tool_use = next(b for b in resp.content if getattr(b, "type", None) == "tool_use")
    return tool_use.input


def select_strategy(state: FollowupState) -> dict[str, Any]:
    days = state["days_since_last_touch"]
    if days > 14:
        return {"strategy": "stop", "should_send": False}
    elif days >= 14:
        strategy = "day_14_breakup"
    elif days >= 7:
        strategy = "day_7_value_add"
    else:
        strategy = "day_3_bump"
    return {"strategy": strategy, "should_send": True}


async def generate_followup(state: FollowupState) -> dict[str, Any]:
    strategy = state["strategy"]

    if strategy == "day_3_bump":
        system_prompt = DAY_3_BUMP_SYSTEM
    elif strategy == "day_7_value_add":
        system_prompt = DAY_7_VALUE_ADD_SYSTEM
    elif strategy == "day_14_breakup":
        system_prompt = DAY_14_BREAKUP_SYSTEM
    else:
        system_prompt = DAY_3_BUMP_SYSTEM

    prior_strategies = [f.get("type") for f in state.get("prior_followups", [])]
    if strategy in prior_strategies:
        system_prompt = system_prompt + "\nAdjust the angle slightly — this strategy was already used."

    original = state["original_email"]
    research = state["research"]
    user_message = (
        f"ORIGINAL EMAIL:\nSubject: {original.get('subject', '')}\n"
        f"Body: {original.get('body', '')}\n\n"
        f"COMPANY RESEARCH:\n{json.dumps(research, indent=2)}\n\n"
        f"STRATEGY: {strategy}\n\n"
        "Generate the follow-up email."
    )

    result = await _call_claude_generate(system_prompt, user_message)
    return {"subject": result.get("subject"), "body": result.get("body")}


def _route_strategy(state: FollowupState) -> str:
    return "stop" if state["strategy"] == "stop" else "generate"


def _build_graph() -> Any:
    builder: StateGraph = StateGraph(FollowupState)
    builder.add_node("select_strategy", select_strategy)
    builder.add_node("generate_followup", generate_followup)
    builder.add_edge(START, "select_strategy")
    builder.add_conditional_edges(
        "select_strategy",
        _route_strategy,
        {"stop": END, "generate": "generate_followup"},
    )
    builder.add_edge("generate_followup", END)
    return builder.compile()


_graph = _build_graph()


async def run_followup_agent(
    lead_id: str,
    days_since_last_touch: int,
    original_email: dict[str, Any],
    prior_followups: list[dict[str, Any]],
    research: dict[str, Any],
) -> FollowupResult:
    initial_state: FollowupState = {
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
    final_state = await _graph.ainvoke(initial_state)
    return FollowupResult(
        should_send=final_state["should_send"],
        subject=final_state.get("subject"),
        body=final_state.get("body"),
        strategy=final_state.get("strategy"),
    )
