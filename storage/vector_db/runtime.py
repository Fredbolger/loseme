import os
from qdrant_client import QdrantClient
from src.core.wiring import build_embedding_provider, build_vector_store

_vector_store = None

def get_vector_store():
    global _vector_store
    if _vector_store is None:
        client = QdrantClient(
            url=os.environ.get("QDRANT_URL", "http://qdrant:6333"),
        )

        _vector_store = build_vector_store(client)
    return _vector_store

def get_embedding_provider():
    return build_embedding_provider()

