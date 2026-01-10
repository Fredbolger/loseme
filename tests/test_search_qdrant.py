import pytest
from storage.vector_db.qdrant_store import QdrantVectorStore
from storage.vector_db.runtime import get_vector_store
from src.domain.models import Chunk
from pipeline.embeddings.dummy import DummyEmbeddingProvider


def test_search_qdrant_returns_results():
    store = get_vector_store()
    store.clear()

    embedder = DummyEmbeddingProvider()

    chunk = Chunk(
        id="c1",
        document_id="d1",
        document_checksum="checksum1",
        content="hello qdrant",
        index=0,
    )

    store.add(chunk, embedder.embed(chunk.content))

    results = store.search(embedder.embed("hello"), top_k=5)

    assert len(results) == 1
    assert results[0].content == "hello qdrant"

