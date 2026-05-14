from typing import Any


async def run_reply_classifier(
    reply_text: str,
    prior_email: str | None = None,
) -> dict[str, Any]:
    """Classify an inbound reply intent.

    Returns:
        Dict with keys: intent, confidence, suggested_next_action, key_phrases.
    """
    raise NotImplementedError
