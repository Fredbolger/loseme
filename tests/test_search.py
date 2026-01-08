from fastapi.testclient import TestClient
from api.app.main import app

client = TestClient(app)

def test_search_returns_results():
    from storage.vector_db.runtime import get_vector_store
    from pipeline.embeddings.dummy import DummyEmbeddingProvider
    from src.domain.models import Chunk

    store = get_vector_store()
    store.clear()

    embedder = DummyEmbeddingProvider()

    chunk = Chunk(
        id="c1",
        document_id="d1",
        content="hello world",
    )

    store.add(chunk, embedder.embed(chunk.content))

    response = client.post("/search", json={"query": "hello"})

    assert response.status_code == 200
    assert len(response.json()["results"]) >= 1

