"""
test_embeddings.py — EmbeddingProvider contracts tested via DummyEmbeddingProvider.

All tests run on CPU with no network.  The contracts verified here apply to
every provider (SentenceTransformer, Nomic, BGE-M3) by the Liskov principle.
"""
import pytest

from pipeline.embeddings.dummy import DummyEmbeddingProvider
from loseme_core.domain import EmbeddingOutput


# ===========================================================================
# DummyEmbeddingProvider
# ===========================================================================

class TestDummyEmbeddingProvider:

    @pytest.fixture
    def provider(self):
        return DummyEmbeddingProvider(dimension=128)

    # --- dimension ---

    def test_dimension_reported_correctly(self, provider):
        assert provider.dimension() == 128

    def test_custom_dimension(self):
        p = DummyEmbeddingProvider(dimension=64)
        assert p.dimension() == 64

    # --- embed_query ---

    def test_embed_query_returns_embedding_output(self, provider):
        result = provider.embed_query("hello world")
        assert isinstance(result, EmbeddingOutput)

    def test_embed_query_dense_correct_length(self, provider):
        result = provider.embed_query("some text")
        assert len(result.dense) == 128

    def test_embed_query_dense_is_list_of_floats(self, provider):
        result = provider.embed_query("some text")
        for v in result.dense:
            assert isinstance(v, float)

    def test_embed_query_values_in_range(self, provider):
        result = provider.embed_query("text")
        for v in result.dense:
            assert -1.0 <= v <= 1.0

    def test_embed_query_deterministic(self, provider):
        a = provider.embed_query("reproducible")
        b = provider.embed_query("reproducible")
        assert a.dense == b.dense

    def test_embed_query_differs_for_different_text(self, provider):
        a = provider.embed_query("hello")
        b = provider.embed_query("world")
        assert a.dense != b.dense

    def test_embed_query_empty_string_does_not_raise(self, provider):
        result = provider.embed_query("")
        assert len(result.dense) == 128

    # --- embed_document ---

    def test_embed_document_returns_embedding_output(self, provider):
        result = provider.embed_document("document text")
        assert isinstance(result, EmbeddingOutput)

    def test_embed_document_dense_correct_length(self, provider):
        result = provider.embed_document("document text")
        assert len(result.dense) == 128

    def test_embed_document_deterministic(self, provider):
        a = provider.embed_document("same doc")
        b = provider.embed_document("same doc")
        assert a.dense == b.dense

    def test_embed_document_differs_from_query_embedding(self, provider):
        """For the dummy provider query == document, but the contract is that both work."""
        q = provider.embed_query("test")
        d = provider.embed_document("test")
        # Both should be EmbeddingOutput with correct dimension
        assert len(q.dense) == len(d.dense) == 128


# ===========================================================================
# EmbeddingOutput model
# ===========================================================================

class TestEmbeddingOutput:

    def test_dense_only_valid(self):
        eo = EmbeddingOutput(dense=[0.1, 0.2, 0.3])
        assert eo.dense == [0.1, 0.2, 0.3]
        assert eo.sparse is None
        assert eo.colbert_vec is None

    def test_all_fields_valid(self):
        eo = EmbeddingOutput(
            dense=[1.0, 0.0],
            sparse={0: 0.5, 1: 0.3},
            colbert_vec=[[0.1, 0.2], [0.3, 0.4]],
        )
        assert eo.dense == [1.0, 0.0]
        assert eo.sparse == {0: 0.5, 1: 0.3}
        assert eo.colbert_vec == [[0.1, 0.2], [0.3, 0.4]]

    def test_extras_stored(self):
        eo = EmbeddingOutput(dense=[1.0], extras={"model": "test"})
        assert eo.extras["model"] == "test"

    def test_empty_dense_allowed(self):
        eo = EmbeddingOutput(dense=[])
        assert eo.dense == []


# ===========================================================================
# Round-trip: embed → store → search (integration without real models)
# ===========================================================================

class TestEmbeddingRoundTrip:

    def test_nearest_neighbour_correct(self):
        """
        Add three chunks with different embeddings.
        The query most similar to chunk0 must rank chunk0 first.
        """
        import hashlib
        from pathlib import Path
        from storage.vector_db.in_memory import InMemoryVectorStore
        from loseme_core.document_models import Chunk
        from loseme_core.ids import make_chunk_id, make_logical_document_part_id, make_source_instance_id

        provider = DummyEmbeddingProvider(dimension=128)
        store = InMemoryVectorStore(dimension=128)

        texts = ["cat", "dog", "banana"]
        chunks = []
        for i, t in enumerate(texts):
            sid = make_source_instance_id("filesystem", "dev1", Path("/tmp"))
            doc_id = make_logical_document_part_id(sid, f"filesystem:/tmp/{i}.txt")
            cid = make_chunk_id(doc_id, hashlib.sha256(t.encode()).hexdigest(), 0)
            chunk = Chunk(
                id=cid,
                source_type="filesystem",
                source_path=f"/tmp/{i}.txt",
                text=t,
                document_part_id=doc_id,
                device_id="dev1",
                unit_locator=f"filesystem:/tmp/{i}.txt",
                index=0,
                metadata={},
            )
            chunks.append(chunk)
            store.add(chunk, provider.embed_document(t))

        query = provider.embed_query("cat")
        results = store.search(query, top_k=3)

        # "cat" should be most similar to itself (deterministic hash embedding)
        assert results[0][0].text == "cat"

    def test_removed_chunk_not_returned(self):
        import hashlib
        from pathlib import Path
        from storage.vector_db.in_memory import InMemoryVectorStore
        from loseme_core.document_models import Chunk
        from loseme_core.ids import make_chunk_id, make_logical_document_part_id, make_source_instance_id

        provider = DummyEmbeddingProvider(dimension=128)
        store = InMemoryVectorStore(dimension=128)

        sid = make_source_instance_id("filesystem", "dev1", Path("/tmp"))
        doc_id = make_logical_document_part_id(sid, "filesystem:/tmp/x.txt")
        cid = make_chunk_id(doc_id, hashlib.sha256(b"x").hexdigest(), 0)
        chunk = Chunk(
            id=cid, source_type="filesystem", source_path="/tmp/x.txt",
            text="x", document_part_id=doc_id, device_id="dev1",
            unit_locator="filesystem:/tmp/x.txt", index=0, metadata={},
        )
        store.add(chunk, provider.embed_document("x"))
        store.remove_chunks([cid])

        results = store.search(provider.embed_query("x"), top_k=10)
        assert all(r[0].id != cid for r in results)
