import os
from qdrant_client import QdrantClient

from storage.vector_db.qdrant_store import QdrantVectorStore
from pipeline.embeddings.dummy import DummyEmbeddingProvider

_vector_store = None
_embedding = DummyEmbeddingProvider()

def get_vector_store():
    global _vector_store
    if _vector_store is None:
        client = QdrantClient(
            url=os.environ.get("QDRANT_URL", "http://qdrant:6333"),
        )
        _vector_store = QdrantVectorStore(client)
    return _vector_store

def get_embedding_provider():
    return _embedding
