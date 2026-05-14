import uuid

from httpx import AsyncClient

from core.config import settings


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


async def test_trigger_research_valid_token_returns_queued(async_client: AsyncClient):
    resp = await async_client.post(
        "/api/internal/trigger-research",
        json={"lead_id": ANY_LEAD_ID},
        headers=VALID_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["queued"] is True
    assert body["data"]["lead_id"] == ANY_LEAD_ID


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
