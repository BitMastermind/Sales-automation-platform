import logging
import uuid
from uuid import UUID
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct

from core.config import settings
from core.embeddings import embed_text

logger = logging.getLogger(__name__)

VECTOR_SIZE = 1536
COLLECTION_COMPANY_RESEARCH = "company_research"
COLLECTION_EMAIL_TEMPLATES = "email_templates"


class VectorStoreClient:
    def __init__(self, client: AsyncQdrantClient | None = None) -> None:
        self._client = client or AsyncQdrantClient(url=settings.qdrant_url)
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        await self.ensure_collections()
        self._initialized = True

    async def ensure_collections(self) -> None:
        for name in (COLLECTION_COMPANY_RESEARCH, COLLECTION_EMAIL_TEMPLATES):
            exists = await self._client.collection_exists(name)
            if not exists:
                await self._client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
                )
                logger.info("Created collection %s", name)

    async def upsert_company_research(
        self, lead_id: UUID, summary_text: str, metadata: dict[str, Any]
    ) -> None:
        await self._ensure_initialized()
        vector = await embed_text(summary_text)
        point = PointStruct(id=lead_id, vector=vector, payload=metadata)
        await self._client.upsert(collection_name=COLLECTION_COMPANY_RESEARCH, points=[point])

    async def search_similar_companies(
        self, query_text: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        await self._ensure_initialized()
        vector = await embed_text(query_text)
        hits = await self._client.search(
            collection_name=COLLECTION_COMPANY_RESEARCH,
            query_vector=vector,
            limit=limit,
        )
        return [hit.payload for hit in hits]

    async def upsert_email_template(self, template_data: dict[str, Any]) -> None:
        await self._ensure_initialized()
        vector = await embed_text(template_data["email_body"])
        point_id = str(uuid.uuid4())
        point = PointStruct(id=point_id, vector=vector, payload=template_data)
        await self._client.upsert(collection_name=COLLECTION_EMAIL_TEMPLATES, points=[point])

    async def get_best_templates(
        self, industry: str, pain_point: str, limit: int = 3
    ) -> list[dict[str, Any]]:
        await self._ensure_initialized()
        vector = await embed_text(f"{industry} {pain_point}")
        hits = await self._client.search(
            collection_name=COLLECTION_EMAIL_TEMPLATES,
            query_vector=vector,
            limit=limit,
        )
        return [hit.payload for hit in hits]


_vector_store: VectorStoreClient | None = None


def get_vector_store() -> VectorStoreClient:
    """Return the process-wide VectorStoreClient singleton.
    Constructed lazily so module import does not require Qdrant to be reachable.
    """
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreClient()
    return _vector_store
