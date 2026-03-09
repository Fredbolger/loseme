"""
Chunker contract tests.

Chunkers are the first place content is shaped for embedding. Both
SimpleTextChunker and SemanticChunker must satisfy a common set of
contracts regardless of their internal strategy:

- Non-empty output for non-empty input
- Empty output for empty input
- Chunk count == text count (parallel lists stay in sync)
- Unique chunk IDs within a single document
- Deterministic IDs across repeated calls
- Individual chunks don't exceed the configured size limit
- Full text coverage (SimpleTextChunker only — semantic merging is allowed)
"""

import pytest

from pipeline.chunking.semantic_chunker import SemanticChunker
from pipeline.chunking.simple_chunker import SimpleTextChunker
from pipeline.embeddings.dummy import DummyEmbeddingProvider
from tests.helpers import make_part

# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

SAMPLE_TEXT = (
    "The quick brown fox jumps over the lazy dog.\n\n"
    "Pack my box with five dozen liquor jugs.\n\n"
    "How vexingly quick daft zebras jump!"
)


# ===========================================================================
# SimpleTextChunker
# ===========================================================================

class TestSimpleTextChunker:

    def test_produces_chunks_for_non_empty_input(self):
        chunker = SimpleTextChunker(chunk_size=50, overlap=10)
        chunks, texts = chunker.chunk(make_part(text=SAMPLE_TEXT))
        assert len(chunks) > 0
        assert len(texts) == len(chunks)

    def test_empty_input_returns_no_chunks(self):
        chunker = SimpleTextChunker()
        chunks, texts = chunker.chunk(make_part(text=""))
        assert chunks == []
        assert texts == []

    def test_covers_full_text_without_overlap(self):
        """With overlap=0 the concatenation of all chunk texts must equal the input."""
        text = "a" * 200
        chunker = SimpleTextChunker(chunk_size=50, overlap=0)
        _, texts = chunker.chunk(make_part(text=text))
        assert "".join(texts) == text, "All input characters must appear in output chunks"

    def test_no_chunk_exceeds_chunk_size(self):
        chunk_size = 50
        chunker = SimpleTextChunker(chunk_size=chunk_size, overlap=10)
        _, texts = chunker.chunk(make_part(text=SAMPLE_TEXT))
        for t in texts:
            assert len(t) <= chunk_size, f"Chunk of length {len(t)} exceeds chunk_size={chunk_size}"

    def test_chunk_ids_are_deterministic(self):
        chunker = SimpleTextChunker(chunk_size=50, overlap=10)
        part = make_part(text=SAMPLE_TEXT)
        ids1 = [c.id for c in chunker.chunk(part)[0]]
        ids2 = [c.id for c in chunker.chunk(part)[0]]
        assert ids1 == ids2

    def test_chunk_ids_are_unique_within_document(self):
        chunker = SimpleTextChunker(chunk_size=20, overlap=0)
        chunks, _ = chunker.chunk(make_part(text="x" * 100))
        ids = [c.id for c in chunks]
        assert len(ids) == len(set(ids)), "Chunk IDs must be unique within a document"

    def test_rejects_overlap_equal_to_chunk_size(self):
        with pytest.raises(ValueError):
            SimpleTextChunker(chunk_size=10, overlap=10)

    def test_rejects_overlap_greater_than_chunk_size(self):
        with pytest.raises(ValueError):
            SimpleTextChunker(chunk_size=10, overlap=15)

    def test_single_chunk_when_text_fits(self):
        text = "short"
        chunker = SimpleTextChunker(chunk_size=100, overlap=0)
        chunks, texts = chunker.chunk(make_part(text=text))
        assert len(chunks) == 1
        assert texts[0] == text

    def test_metadata_records_start_and_end(self):
        chunker = SimpleTextChunker(chunk_size=50, overlap=0)
        chunks, _ = chunker.chunk(make_part(text="a" * 100))
        for chunk in chunks:
            assert "start" in chunk.metadata
            assert "end" in chunk.metadata


# ===========================================================================
# SemanticChunker
# ===========================================================================

class TestSemanticChunker:

    @pytest.fixture
    def chunker(self):
        return SemanticChunker(
            embedder=DummyEmbeddingProvider(),
            max_chars=200,
            similarity_threshold=0.75,
        )

    def test_produces_chunks_for_non_empty_input(self, chunker):
        chunks, texts = chunker.chunk(make_part(text=SAMPLE_TEXT))
        assert len(chunks) > 0
        assert len(texts) == len(chunks)

    def test_empty_input_returns_no_chunks(self, chunker):
        chunks, texts = chunker.chunk(make_part(text=""))
        assert chunks == []
        assert texts == []

    def test_chunk_ids_are_deterministic(self, chunker):
        part = make_part(text=SAMPLE_TEXT)
        ids1 = [c.id for c in chunker.chunk(part)[0]]
        ids2 = [c.id for c in chunker.chunk(part)[0]]
        assert ids1 == ids2

    def test_no_chunk_exceeds_max_chars(self):
        max_chars = 60
        chunker = SemanticChunker(
            embedder=DummyEmbeddingProvider(),
            max_chars=max_chars,
        )
        _, texts = chunker.chunk(make_part(text=SAMPLE_TEXT))
        for t in texts:
            assert len(t) <= max_chars, f"Chunk of length {len(t)} exceeds max_chars={max_chars}"

    def test_chunk_ids_are_unique_within_document(self, chunker):
        chunks, _ = chunker.chunk(make_part(text=SAMPLE_TEXT))
        ids = [c.id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_single_paragraph_produces_one_chunk(self, chunker):
        text = "One single paragraph with no double newlines at all."
        chunks, _ = chunker.chunk(make_part(text=text))
        assert len(chunks) == 1

    def test_chunk_text_field_matches_text_list(self, chunker):
        """chunk.text and the parallel texts list must stay in sync."""
        chunks, texts = chunker.chunk(make_part(text=SAMPLE_TEXT))
        for chunk, text in zip(chunks, texts):
            assert chunk.text == text
