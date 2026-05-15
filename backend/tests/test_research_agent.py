"""Tests for the Research Agent (Phase 3A)."""
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from core.exceptions import AgentOutputError, register_exception_handlers


async def test_agent_output_error_handler_returns_422_envelope():
    """The AgentOutputError handler returns a 422 with the standard envelope.

    Uses a self-contained FastAPI app so the global app singleton is never mutated.
    """
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/__raise__")
    async def _raise():
        raise AgentOutputError(agent="research", violations=["x"])

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        resp = await client.get("/__raise__")

    assert resp.status_code == 422
    body = resp.json()
    assert body["data"] is None
    assert body["error"]["code"] == "AGENT_OUTPUT_ERROR"
    assert "research" in body["error"]["message"]
    assert body["error"]["details"]["agent"] == "research"
    assert body["error"]["details"]["violations"] == ["x"]
    assert body["meta"] == {}
