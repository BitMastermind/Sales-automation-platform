"""Tests for the Research Agent (Phase 3A)."""
from httpx import AsyncClient


async def test_agent_output_error_handler_returns_422_envelope(async_client: AsyncClient):
    """The AgentOutputError handler returns a 422 with the standard envelope.

    We trigger it via a temporary route appended in the test (no real agent yet).
    """
    from main import app
    from core.exceptions import AgentOutputError

    @app.get("/__test_agent_error__")
    async def _raise():
        raise AgentOutputError(agent="research", violations=["x"])

    try:
        resp = await async_client.get("/__test_agent_error__")
        assert resp.status_code == 422
        body = resp.json()
        assert body["data"] is None
        assert body["error"]["code"] == "AGENT_OUTPUT_ERROR"
        assert body["error"]["details"]["agent"] == "research"
        assert body["error"]["details"]["violations"] == ["x"]
        assert body["meta"] == {}
    finally:
        # Remove the test-only route so it doesn't leak into other tests
        app.router.routes = [r for r in app.router.routes if getattr(r, "path", None) != "/__test_agent_error__"]
