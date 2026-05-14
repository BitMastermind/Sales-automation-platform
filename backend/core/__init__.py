from core.vector_store import VectorStoreClient

_instance: VectorStoreClient | None = None


def get_vector_store() -> VectorStoreClient:
    global _instance
    if _instance is None:
        _instance = VectorStoreClient()
    return _instance
