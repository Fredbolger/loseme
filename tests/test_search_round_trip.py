"""
Search round-trip tests.

If ingest succeeds but search returns nothing, the system is broken from
the user's perspective without surfacing any error. These tests exercise
the full vertical slice: ingest → vector store → search API response.

An InMemoryVectorStore + DummyEmbeddingProvider are injected so the suite
runs without a live Qdrant instance.
"""

import pytest

from src.sources.filesystem.filesystem_model import FilesystemIndexingScope
from storage.metadata_db.indexing_runs import create_run, load_latest_run_by_scope
from tests.helpers import client, ingest_part, make_part


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def use_in_memory_store(monkeypatch):
    """Swap Qdrant for an in-memory store backed by the DummyEmbeddingProvider."""
    from pipeline.embeddings.dummy import DummyEmbeddingProvider
    from storage.vector_db.in_memory import InMemoryVectorStore

    store = InMemoryVectorStore(dimension=384)
    embedder = DummyEmbeddingProvider(dimension=384)

    monkeypatch.setattr("storage.vector_db.runtime.get_vector_store", lambda: store)
    monkeypatch.setattr("storage.vector_db.runtime.get_embedding_provider", lambda: embedder)
    return store


@pytest.fixture
def run_id(setup_db):
    scope = FilesystemIndexingScope(type="filesystem", directories=["/tmp/search-tests"])
    create_run("filesystem", scope)
    return load_latest_run_by_scope(scope).id


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ingest_and_search(part, run_id, query: str, top_k: int = 5):
    ingest_part(part, run_id)
    resp = client.post("/search", json={"query": query, "top_k": top_k})
    assert resp.status_code == 200
    return resp.json()["results"]


# ===========================================================================
# Basic API contract
# ===========================================================================

class TestSearchApiContract:

    def test_returns_200(self):
        resp = client.post("/search", json={"query": "anything", "top_k": 5})
        assert resp.status_code == 200

    def test_response_has_results_key(self):
        resp = client.post("/search", json={"query": "anything", "top_k": 5})
        assert "results" in resp.json()

    def test_results_is_a_list(self):
        resp = client.post("/search", json={"query": "anything", "top_k": 5})
        assert isinstance(resp.json()["results"], list)

    def test_empty_index_returns_empty_results(self):
        resp = client.post("/search", json={"query": "anything", "top_k": 5})
        assert resp.json()["results"] == []

    def test_result_has_required_fields(self, run_id):
        part = make_part(text="The result shape must be validated.")
        results = _ingest_and_search(part, run_id, "result shape")
        assert len(results) > 0
        required = {"chunk_id", "document_part_id", "device_id", "score", "metadata"}
        for r in results:
            assert required.issubset(r.keys()), f"Missing fields: {required - r.keys()}"


# ===========================================================================
# Retrieval correctness
# ===========================================================================

class TestRetrievalCorrectness:

    def test_ingested_document_appears_in_results(self, run_id):
        part = make_part(text="Neural networks learn representations from data.")
        results = _ingest_and_search(part, run_id, "neural networks")
        part_ids = [r["document_part_id"] for r in results]
        assert part.document_part_id in part_ids, (
            "The ingested document must appear in search results"
        )

    def test_top_k_limits_result_count(self, run_id):
        for i in range(6):
            ingest_part(
                make_part(
                    text=f"Document {i} about various topics.",
                    unit_locator=f"filesystem:/tmp/doc{i}.txt",
                ),
                run_id,
            )
        top_k = 3
        resp = client.post("/search", json={"query": "document", "top_k": top_k})
        assert len(resp.json()["results"]) <= top_k

    def test_scores_are_in_valid_range(self, run_id):
        part = make_part(text="Score range validation content.")
        ingest_part(part, run_id)
        resp = client.post("/search", json={"query": "score", "top_k": 5})
        for r in resp.json()["results"]:
            assert -1.0 <= r["score"] <= 1.0, f"Score out of cosine range: {r['score']}"

    def test_device_id_is_preserved_in_results(self, run_id):
        part = make_part(text="Device ID propagation check.", device_id="my-laptop")
        results = _ingest_and_search(part, run_id, "device propagation")
        matching = [r for r in results if r["document_part_id"] == part.document_part_id]
        assert matching, "Ingested part not found in results"
        assert matching[0]["device_id"] == "my-laptop"

    def test_multiple_documents_all_retrievable(self, run_id):
        parts = [
            make_part(
                text=f"Unique content about topic number {i}.",
                unit_locator=f"filesystem:/tmp/multi{i}.txt",
            )
            for i in range(3)
        ]
        for p in parts:
            ingest_part(p, run_id)

        resp = client.post("/search", json={"query": "unique content topic", "top_k": 10})
        returned_ids = {r["document_part_id"] for r in resp.json()["results"]}
        for p in parts:
            assert p.document_part_id in returned_ids, (
                f"Part {p.document_part_id} not found in search results"
            )
