import pytest
from unittest.mock import AsyncMock, patch
from qdrant_client.http.models import ScoredPoint

from core.vector_store import VectorStoreClient


FAKE_VEC = [0.1] * 1536


@pytest.fixture
def mock_qdrant():
    client = AsyncMock()
    client.collection_exists.return_value = True
    return client


@pytest.mark.asyncio
async def test_upsert_and_search_company(mock_qdrant):
    lead_id = "11111111-1111-1111-1111-111111111111"
    expected_payload = {
        "company_name": "Acme Corp",
        "website": "acme.com",
        "lead_id": lead_id,
        "research_summary": "Acme is a widget manufacturer.",
        "timestamp": "2024-01-01T00:00:00Z",
    }
    mock_qdrant.search.return_value = [
        ScoredPoint(id=lead_id, version=0, score=0.95, payload=expected_payload, vector=None)
    ]

    with patch("core.vector_store.embed_text", new_callable=AsyncMock, return_value=FAKE_VEC):
        store = VectorStoreClient(client=mock_qdrant)
        await store.upsert_company_research(lead_id, "Acme is a widget manufacturer.", expected_payload)
        results = await store.search_similar_companies("widget manufacturer", limit=1)

    assert len(results) == 1
    assert results[0]["company_name"] == "Acme Corp"
    assert results[0]["lead_id"] == lead_id
    mock_qdrant.upsert.assert_awaited_once()
    mock_qdrant.search.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_best_templates(mock_qdrant):
    template_saas = {
        "industry": "SaaS",
        "pain_point": "churn",
        "email_body": "We help SaaS companies reduce churn.",
        "reply_rate": 0.12,
    }
    template_fintech = {
        "industry": "FinTech",
        "pain_point": "compliance",
        "email_body": "Automate your compliance workflows.",
        "reply_rate": 0.08,
    }
    mock_qdrant.search.return_value = [
        ScoredPoint(id="aaaa", version=0, score=0.91, payload=template_saas, vector=None),
        ScoredPoint(id="bbbb", version=0, score=0.72, payload=template_fintech, vector=None),
    ]

    with patch("core.vector_store.embed_text", new_callable=AsyncMock, return_value=FAKE_VEC):
        store = VectorStoreClient(client=mock_qdrant)
        await store.upsert_email_template(template_saas)
        await store.upsert_email_template(template_fintech)
        results = await store.get_best_templates("SaaS", "churn", limit=2)

    assert len(results) == 2
    assert results[0]["industry"] == "SaaS"
    assert results[0]["reply_rate"] == 0.12
    assert results[1]["industry"] == "FinTech"
    assert mock_qdrant.upsert.await_count == 2


def test_get_vector_store_returns_singleton():
    from core.vector_store import get_vector_store, VectorStoreClient

    a = get_vector_store()
    b = get_vector_store()
    assert isinstance(a, VectorStoreClient)
    assert a is b
