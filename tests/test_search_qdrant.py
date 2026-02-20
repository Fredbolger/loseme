import pytest
import os 
from storage.vector_db.qdrant_store import QdrantVectorStore
from storage.vector_db.runtime import get_vector_store
from src.sources.base.models import Chunk, Document
from src.core.wiring import build_embedding_provider
from storage.vector_db.runtime import get_vector_store

device_id = os.getenv("LOSEME_DEVICE_ID")

def test_search_qdrant_returns_results(setup_db):
    store = get_vector_store()

    embedder = build_embedding_provider()

    chunk = Chunk(
        id="c1",
        source_type="filesystem",
        document_part_id="d1",
        device_id=device_id,
        unit_locator="loc1",
        index=0,
    )

    query_embed = embedder.embed_query("hello qdrant")
    store.add(chunk, query_embed)
    results = store.search(query_embed, top_k=5)

    assert len(results) == 1
    # test that the result[0][0] is the same chunk we added
    assert results[0][0].id == chunk.id
