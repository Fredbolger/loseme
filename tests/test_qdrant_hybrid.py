import os
import pytest
from unittest.mock import patch
from qdrant_client import QdrantClient
from storage.vector_db.qdrant_store_hybrid import QdrantVectorStoreHybrid
from src.sources.base.models import Chunk
pytest.importorskip("QdrantVectorStoreHybrid")
from src.core.wiring import build_embedding_provider
import logging
logger = logging.getLogger(__name__)

@pytest.fixture
def qdrant_client():
    client = QdrantClient(
        url=os.environ.get("QDRANT_URL", "http://qdrant:6333"),
    )
    # patch the ps variable VECTOR_SIZE to 1024 for testing
    with patch('storage.vector_db.qdrant_store_hybrid.VECTOR_SIZE', 1024):
        yield client

def test_init_qdrant_store_hybrid(qdrant_client):
    store = QdrantVectorStoreHybrid(qdrant_client)
    assert store is not None

def test_ingest_document(qdrant_client, setup_db, set_embedding_model_env):
    store = QdrantVectorStoreHybrid(qdrant_client)
    store.delete_collection()  # Clean slate for the test

    assert os.getenv("EMBEDDING_MODEL") == "bge-m3"

    # Define the hybrid embedding provider
    embedder = build_embedding_provider()

    assert embedder.model_name == "BAAI/bge-m3"
    
    # Create a mock chunk and embedding
    chunk = Chunk(
        id="chunk_hybrid_1",
        source_type="filesystem",
        document_id="doc_hybrid_1",
        device_id="device_hybrid_1",
        index=0,
    )
    embedding = embedder.embed_query("This is a test chunk for hybrid embedding.")
    store.add(chunk, embedding)

def test_search_qdrant_hybrid(qdrant_client, setup_db, set_embedding_model_env):
    store = QdrantVectorStoreHybrid(qdrant_client)
        
    embedder = build_embedding_provider()

    chunk = Chunk(
        id="chunk_hybrid_2",
        source_type="filesystem",
        source_path="/path/to/hybrid/file",
        document_id="doc_hybrid_2",
        device_id="device_hybrid_2",
        index=0,
    )

    query_embed = embedder.embed_query("test chunk hybrid embedding")
    store.add(chunk, query_embed)
    results = store.search(query_embed, top_k=5)

    assert len(results) >= 1
    # test that the result[0][0] is the same chunk we added
    assert results[0][0].id == chunk.id
