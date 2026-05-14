from httpx import AsyncClient


async def _make_campaign(client: AsyncClient) -> str:
    resp = await client.post("/api/campaigns", json={"name": "Lead Test Campaign"})
    return resp.json()["data"]["id"]


async def test_upload_valid_csv_inserts_leads(async_client: AsyncClient):
    cid = await _make_campaign(async_client)
    csv = "company_name,email,website,contact_name\nAcme Corp,ceo@acme.com,acme.com,John\n"

    resp = await async_client.post(
        "/api/leads/upload",
        files={"file": ("leads.csv", csv.encode(), "text/csv")},
        data={"campaign_id": cid},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["inserted"] == 1
    assert body["data"]["skipped"] == 0
    assert body["data"]["errors"] == []


async def test_upload_csv_skips_invalid_email(async_client: AsyncClient):
    cid = await _make_campaign(async_client)
    csv = "company_name,email\nAcme,valid@acme.com\nBad Corp,not-an-email\n"

    resp = await async_client.post(
        "/api/leads/upload",
        files={"file": ("leads.csv", csv.encode(), "text/csv")},
        data={"campaign_id": cid},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["inserted"] == 1
    assert body["data"]["skipped"] == 1
    assert len(body["data"]["errors"]) == 1
    assert body["data"]["errors"][0]["reason"] == "invalid email"


async def test_upload_csv_missing_required_column_returns_400(async_client: AsyncClient):
    cid = await _make_campaign(async_client)
    csv = "company_name,phone\nAcme,555-1234\n"

    resp = await async_client.post(
        "/api/leads/upload",
        files={"file": ("leads.csv", csv.encode(), "text/csv")},
        data={"campaign_id": cid},
    )
    assert resp.status_code == 400


async def test_list_leads_filtered_by_campaign(async_client: AsyncClient):
    cid = await _make_campaign(async_client)
    csv = "company_name,email\nAcme,a@acme.com\nBeta,b@beta.com\n"
    await async_client.post(
        "/api/leads/upload",
        files={"file": ("leads.csv", csv.encode(), "text/csv")},
        data={"campaign_id": cid},
    )

    resp = await async_client.get(f"/api/leads?campaign_id={cid}&page=1&size=20")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 2
    assert body["meta"]["total"] == 2


async def test_get_lead_detail_includes_emails(async_client: AsyncClient):
    cid = await _make_campaign(async_client)
    csv = "company_name,email\nAcme,a@acme.com\n"
    await async_client.post(
        "/api/leads/upload",
        files={"file": ("leads.csv", csv.encode(), "text/csv")},
        data={"campaign_id": cid},
    )

    list_resp = await async_client.get(f"/api/leads?campaign_id={cid}&page=1&size=20")
    lid = list_resp.json()["data"][0]["id"]

    resp = await async_client.get(f"/api/leads/{lid}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["id"] == lid
    assert isinstance(body["data"]["emails"], list)
