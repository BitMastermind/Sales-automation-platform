"""Reply Classifier — Phase 3D.

Single structured GPT-4o-mini call. No graph. The Pydantic model enforces the
intent -> suggested_next_action mapping server-side so we never trust the LLM
to return the right action.
"""
from __future__ import annotations

import json
import logging
from typing import Literal

import openai
from pydantic import BaseModel, Field, model_validator
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from agents.prompts.classifier_prompts import CLASSIFY_SYSTEM

logger = logging.getLogger(__name__)

Intent = Literal[
    "interested",
    "not_interested",
    "meeting_request",
    "unsubscribe",
    "needs_more_info",
    "unknown",
]

NextAction = Literal[
    "schedule_call",
    "send_followup",
    "close_lead",
    "unsubscribe_lead",
    "reply_with_info",
    "wait",
]

INTENT_TO_ACTION: dict[str, str] = {
    "interested": "schedule_call",
    "not_interested": "close_lead",
    "meeting_request": "schedule_call",
    "unsubscribe": "unsubscribe_lead",
    "needs_more_info": "reply_with_info",
    "unknown": "wait",
}


class ClassificationResult(BaseModel):
    intent: Intent
    confidence: float = Field(ge=0.0, le=1.0)
    suggested_next_action: NextAction
    key_phrases: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _enforce_action_mapping(self) -> "ClassificationResult":
        canonical = INTENT_TO_ACTION[self.intent]
        if self.suggested_next_action != canonical:
            logger.warning(
                "classifier returned action=%s for intent=%s; overriding to %s",
                self.suggested_next_action,
                self.intent,
                canonical,
            )
            self.suggested_next_action = canonical  # type: ignore[assignment]
        return self


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
async def run_reply_classifier(
    reply_text: str,
    prior_email: str | None = None,
) -> ClassificationResult:
    """Classify an inbound reply intent via a single GPT-4o-mini structured call."""
    from core.config import settings

    client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    user_parts = [f"Reply:\n{reply_text}"]
    if prior_email:
        user_parts.append(f"\nPrior email (for context):\n{prior_email}")

    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": CLASSIFY_SYSTEM},
            {"role": "user", "content": "\n".join(user_parts)},
        ],
    )
    payload = json.loads(resp.choices[0].message.content)
    return ClassificationResult.model_validate(payload)
