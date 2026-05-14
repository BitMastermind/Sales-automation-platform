from httpx import AsyncClient


async def test_create_campaign(async_client: AsyncClient):
    resp = await async_client.post("/api/campaigns", json={"name": "Alpha Campaign"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["data"]["name"] == "Alpha Campaign"
    assert body["data"]["status"] == "draft"
    assert body["error"] is None


async def test_create_campaign_missing_name_returns_422(async_client: AsyncClient):
    resp = await async_client.post("/api/campaigns", json={})
    assert resp.status_code == 422


async def test_list_campaigns_paginated_with_stats(async_client: AsyncClient):
    await async_client.post("/api/campaigns", json={"name": "Camp A"})
    await async_client.post("/api/campaigns", json={"name": "Camp B"})

    resp = await async_client.get("/api/campaigns?page=1&size=20")
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["total"] == 2
    assert body["meta"]["page"] == 1
    assert body["meta"]["size"] == 20
    assert len(body["data"]) == 2

    item = body["data"][0]
    assert "stats" in item
    for key in ("leads_count", "emails_sent", "open_rate", "reply_rate", "meetings_booked"):
        assert key in item["stats"]


async def test_get_campaign_by_id(async_client: AsyncClient):
    cr = await async_client.post("/api/campaigns", json={"name": "Get Me"})
    cid = cr.json()["data"]["id"]

    resp = await async_client.get(f"/api/campaigns/{cid}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["id"] == cid
    assert "stats" in body["data"]


async def test_get_campaign_not_found(async_client: AsyncClient):
    resp = await async_client.get("/api/campaigns/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


async def test_patch_campaign_status_to_active(async_client: AsyncClient):
    cr = await async_client.post("/api/campaigns", json={"name": "Status Test"})
    cid = cr.json()["data"]["id"]

    resp = await async_client.patch(f"/api/campaigns/{cid}/status", json={"status": "active"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["status"] == "active"
    assert body["error"] is None


async def test_patch_campaign_status_invalid_value_returns_422(async_client: AsyncClient):
    cr = await async_client.post("/api/campaigns", json={"name": "Bad Status"})
    cid = cr.json()["data"]["id"]

    resp = await async_client.patch(f"/api/campaigns/{cid}/status", json={"status": "unknown"})
    assert resp.status_code == 422
