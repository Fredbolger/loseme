"""
test_vector_store.py — InMemoryVectorStore unit tests.

No Qdrant, no network.  Tests the store used in CI and the fallback store
used in tests throughout the project.
"""
import math
import hashlib
from pathlib import Path

import pytest

from storage.vector_db.in_memory import InMemoryVectorStore
from loseme_core.document_models import Chunk
from loseme_core.ids import make_chunk_id, make_logical_document_part_id, make_source_instance_id
from loseme_core.domain import EmbeddingOutput


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DIM = 8  # tiny dimension for speed


def _vec(*values) -> EmbeddingOutput:
    """Build an EmbeddingOutput with a dense vector from the given floats."""
    return EmbeddingOutput(dense=list(values))


def _unit(values) -> EmbeddingOutput:
    """Normalise a list of floats to unit length, return EmbeddingOutput."""
    mag = math.sqrt(sum(v * v for v in values))
    return EmbeddingOutput(dense=[v / mag for v in values])


def _make_chunk(idx: int = 0, text: str = "chunk text") -> Chunk:
    sid = make_source_instance_id("filesystem", "dev1", Path("/tmp"))
    doc_id = make_logical_document_part_id(sid, f"filesystem:/tmp/doc{idx}.txt")
    cid = make_chunk_id(doc_id, hashlib.sha256(text.encode()).hexdigest(), idx)
    return Chunk(
        id=cid,
        source_type="filesystem",
        source_path=f"/tmp/doc{idx}.txt",
        text=text,
        document_part_id=doc_id,
        device_id="dev1",
        unit_locator=f"filesystem:/tmp/doc{idx}.txt",
        index=idx,
        metadata={"char_len": len(text)},
    )


def _store() -> InMemoryVectorStore:
    return InMemoryVectorStore(dimension=DIM)


# ===========================================================================
# Construction
# ===========================================================================

class TestConstruction:

    def test_empty_on_creation(self):
        store = _store()
        results = store.search(EmbeddingOutput(dense=[0.0] * DIM), top_k=10)
        assert results == []

    def test_dimension_reported_correctly(self):
        store = InMemoryVectorStore(dimension=16)
        assert store.dimension() == 16


# ===========================================================================
# add / dimension mismatch
# ===========================================================================

class TestAdd:

    def test_add_and_retrieve_via_search(self):
        store = _store()
        chunk = _make_chunk(0, "hello world")
        vec = _unit([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        store.add(chunk, vec)
        results = store.search(vec, top_k=1)
        assert len(results) == 1
        assert results[0][0].id == chunk.id

    def test_add_wrong_dimension_raises(self):
        store = _store()
        chunk = _make_chunk(0)
        bad_vec = EmbeddingOutput(dense=[1.0] * (DIM + 1))
        with pytest.raises(ValueError):
            store.add(chunk, bad_vec)

    def test_duplicate_id_replaced(self):
        store = _store()
        chunk = _make_chunk(0, "original")
        vec1 = _unit([1, 0, 0, 0, 0, 0, 0, 0])
        vec2 = _unit([0, 1, 0, 0, 0, 0, 0, 0])
        store.add(chunk, vec1)
        store.add(chunk, vec2)
        # Only one entry should exist
        results = store.search(vec2, top_k=10)
        ids = [r[0].id for r in results]
        assert ids.count(chunk.id) == 1

    def test_multiple_chunks_all_stored(self):
        store = _store()
        chunks = [_make_chunk(i, f"text {i}") for i in range(5)]
        for i, c in enumerate(chunks):
            v = [0.0] * DIM
            v[i % DIM] = 1.0
            store.add(c, EmbeddingOutput(dense=v))
        results = store.search(EmbeddingOutput(dense=[1.0] + [0.0] * (DIM - 1)), top_k=10)
        assert len(results) == 5


# ===========================================================================
# search
# ===========================================================================

class TestSearch:

    def test_top_k_limits_results(self):
        store = _store()
        for i in range(10):
            v = [0.0] * DIM
            v[i % DIM] += 1.0
            store.add(_make_chunk(i, f"t{i}"), EmbeddingOutput(dense=v))
        results = store.search(EmbeddingOutput(dense=[1.0] + [0.0] * (DIM - 1)), top_k=3)
        assert len(results) <= 3

    def test_results_ordered_by_score_descending(self):
        store = _store()
        # chunk0 is perfectly aligned with query; others diverge
        q = [1.0] + [0.0] * (DIM - 1)
        for i in range(4):
            v = [0.0] * DIM
            v[i] = 1.0
            store.add(_make_chunk(i, f"t{i}"), EmbeddingOutput(dense=v))
        results = store.search(EmbeddingOutput(dense=q), top_k=4)
        scores = [r[1] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_scores_in_cosine_range(self):
        store = _store()
        vecs = [
            [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [-1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        ]
        for i, v in enumerate(vecs):
            store.add(_make_chunk(i, f"t{i}"), EmbeddingOutput(dense=v))
        query = EmbeddingOutput(dense=[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        for _, score in store.search(query, top_k=10):
            assert -1.0 <= score <= 1.0 + 1e-9

    def test_zero_vector_returns_zero_scores(self):
        store = _store()
        store.add(_make_chunk(0), EmbeddingOutput(dense=[1.0] + [0.0] * (DIM - 1)))
        zero = EmbeddingOutput(dense=[0.0] * DIM)
        results = store.search(zero, top_k=1)
        assert results[0][1] == 0.0

    def test_search_wrong_dimension_raises(self):
        store = _store()
        bad = EmbeddingOutput(dense=[1.0] * (DIM + 2))
        with pytest.raises(ValueError):
            store.search(bad, top_k=1)

    def test_exact_match_scores_one(self):
        store = _store()
        v = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        chunk = _make_chunk(0, "exact")
        store.add(chunk, EmbeddingOutput(dense=v))
        results = store.search(EmbeddingOutput(dense=v), top_k=1)
        assert abs(results[0][1] - 1.0) < 1e-6

    def test_top_k_zero_returns_empty(self):
        store = _store()
        store.add(_make_chunk(0), EmbeddingOutput(dense=[1.0] + [0.0] * (DIM - 1)))
        results = store.search(EmbeddingOutput(dense=[1.0] + [0.0] * (DIM - 1)), top_k=0)
        assert results == []


# ===========================================================================
# remove_chunks
# ===========================================================================

class TestRemoveChunks:

    def test_removed_chunk_not_in_results(self):
        store = _store()
        c = _make_chunk(0, "to remove")
        v = EmbeddingOutput(dense=[1.0] + [0.0] * (DIM - 1))
        store.add(c, v)
        store.remove_chunks([c.id])
        results = store.search(v, top_k=10)
        assert all(r[0].id != c.id for r in results)

    def test_remove_unknown_id_is_noop(self):
        store = _store()
        store.add(_make_chunk(0), EmbeddingOutput(dense=[1.0] + [0.0] * (DIM - 1)))
        store.remove_chunks(["nonexistent-id"])  # must not raise
        assert len(store.search(EmbeddingOutput(dense=[1.0] + [0.0] * (DIM - 1)), top_k=10)) == 1

    def test_remove_subset_leaves_others(self):
        store = _store()
        chunks = [_make_chunk(i, f"t{i}") for i in range(3)]
        for i, c in enumerate(chunks):
            v = [0.0] * DIM; v[i] = 1.0
            store.add(c, EmbeddingOutput(dense=v))
        store.remove_chunks([chunks[0].id])
        results = store.search(EmbeddingOutput(dense=[0.0, 1.0] + [0.0] * (DIM - 2)), top_k=10)
        ids = {r[0].id for r in results}
        assert chunks[0].id not in ids
        assert chunks[1].id in ids


# ===========================================================================
# clear
# ===========================================================================

class TestClear:

    def test_clear_empties_store(self):
        store = _store()
        store.add(_make_chunk(0), EmbeddingOutput(dense=[1.0] + [0.0] * (DIM - 1)))
        store.clear()
        results = store.search(EmbeddingOutput(dense=[1.0] + [0.0] * (DIM - 1)), top_k=10)
        assert results == []

    def test_add_after_clear_works(self):
        store = _store()
        store.add(_make_chunk(0), EmbeddingOutput(dense=[1.0] + [0.0] * (DIM - 1)))
        store.clear()
        c2 = _make_chunk(1, "after clear")
        v = EmbeddingOutput(dense=[0.0, 1.0] + [0.0] * (DIM - 2))
        store.add(c2, v)
        results = store.search(v, top_k=1)
        assert results[0][0].id == c2.id
