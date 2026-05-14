import httpx

from core.config import settings

EMBEDDING_MODEL = "text-embedding-3-small"
OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"


async def embed_text(text: str) -> list[float]:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            OPENAI_EMBEDDINGS_URL,
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={"input": text, "model": EMBEDDING_MODEL},
        )
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]
