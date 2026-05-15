import uuid
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from core.config import settings
from core.exceptions import AgentOutputError


VALID_HEADERS = {"X-Internal-Token": settings.internal_api_token}
ANY_LEAD_ID = str(uuid.uuid4())


async def test_trigger_research_missing_token_returns_401(async_client: AsyncClient):
    resp = await async_client.post(
        "/api/internal/trigger-research", json={"lead_id": ANY_LEAD_ID}
    )
    assert resp.status_code == 401


async def test_trigger_research_wrong_token_returns_401(async_client: AsyncClient):
    resp = await async_client.post(
        "/api/internal/trigger-research",
        json={"lead_id": ANY_LEAD_ID},
        headers={"X-Internal-Token": "wrong-token"},
    )
    assert resp.status_code == 401


async def test_trigger_research_valid_token_returns_real_research(async_client: AsyncClient):
    canned = {
        "industry": "SaaS", "company_size": "50-200",
        "pain_points": ["a", "b"], "recent_news": [],
        "tech_stack": [],
        "research_summary": "Acme is a SaaS firm based in Denver with a recent expansion in Q1 2025.",
    }
    with patch("api.internal.trigger_research_iface",
               new=AsyncMock(return_value=canned)):
        resp = await async_client.post(
            "/api/internal/trigger-research",
            json={"lead_id": ANY_LEAD_ID},
            headers=VALID_HEADERS,
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"] == canned
    assert body["error"] is None


async def test_trigger_research_returns_404_when_lead_missing(async_client: AsyncClient):
    with patch("api.internal.trigger_research_iface",
               new=AsyncMock(side_effect=LookupError("Lead xyz not found"))):
        resp = await async_client.post(
            "/api/internal/trigger-research",
            json={"lead_id": ANY_LEAD_ID},
            headers=VALID_HEADERS,
        )

    assert resp.status_code == 404


async def test_trigger_research_agent_output_error_returns_422(async_client: AsyncClient):
    with patch("api.internal.trigger_research_iface",
               new=AsyncMock(side_effect=AgentOutputError("research", ["quality_check_failed_after_2_refines"]))):
        resp = await async_client.post(
            "/api/internal/trigger-research",
            json={"lead_id": ANY_LEAD_ID},
            headers=VALID_HEADERS,
        )

    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "AGENT_OUTPUT_ERROR"
    assert body["error"]["details"]["agent"] == "research"


async def test_trigger_personalization_valid_token(async_client: AsyncClient):
    resp = await async_client.post(
        "/api/internal/trigger-personalization",
        json={"lead_id": ANY_LEAD_ID},
        headers=VALID_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["queued"] is True


async def test_trigger_followup_valid_token(async_client: AsyncClient):
    resp = await async_client.post(
        "/api/internal/trigger-followup",
        json={"lead_id": ANY_LEAD_ID},
        headers=VALID_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["queued"] is True


async def test_leads_needing_followup_missing_token_returns_401(async_client: AsyncClient):
    resp = await async_client.get("/api/internal/leads-needing-followup")
    assert resp.status_code == 401


async def test_leads_needing_followup_valid_token_returns_list(async_client: AsyncClient):
    resp = await async_client.get(
        "/api/internal/leads-needing-followup", headers=VALID_HEADERS
    )
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"], list)
