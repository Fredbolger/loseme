import pytest
import os 
from storage.vector_db.qdrant_store import QdrantVectorStore
from storage.vector_db.runtime import get_vector_store
from src.domain.models import Chunk, Document
from pipeline.embeddings.sentence_transformer import SentenceTransformerEmbeddingProvider

device_id = os.getenv("LOSEME_DEVICE_ID")

def test_search_qdrant_returns_results():
    store = get_vector_store()
    store.clear()

    embedder = SentenceTransformerEmbeddingProvider()

    chunk = Chunk(
        id="c1",
        document_id="d1",
        #document_checksum="checksum1",
        device_id=device_id,
        #source_path="/path/to/doc1.txt",
        index=0,
    )

    query_embed = embedder.embed_query("hello qdrant")
    store.add(chunk, query_embed)
    results = store.search(query_embed, top_k=5)

    assert len(results) == 1
    # test that the result[0][0] is the same chunk we added
    assert results[0][0].id == chunk.id

    # Clean up
    store.clear()
