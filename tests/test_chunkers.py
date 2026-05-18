"""
test_chunkers.py — Chunker contract tests (CPU-only, no ML models).

SimpleTextChunker and SentenceAwareChunker must satisfy identical contracts.
SemanticChunker is covered via DummyEmbeddingProvider so no GPU is required.
"""
import hashlib
from pathlib import Path

import pytest

from loseme_core.ids import make_logical_document_part_id, make_source_instance_id
from loseme_core.document_models import DocumentPart


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_part(text: str, unit_locator: str = "filesystem:/tmp/doc.txt") -> DocumentPart:
    sid = make_source_instance_id("filesystem", "dev1", Path("/tmp"))
    doc_id = make_logical_document_part_id(sid, unit_locator)
    checksum = hashlib.sha256(text.encode()).hexdigest()
    return DocumentPart(
        text=text,
        document_part_id=doc_id,
        checksum=checksum,
        source_type="filesystem",
        source_instance_id=sid,
        device_id="dev1",
        source_path="/tmp/doc.txt",
        unit_locator=unit_locator,
        content_type="text/plain",
        extractor_name="plaintext",
        extractor_version="0.1",
        scope_json={"type": "filesystem", "directories": ["/tmp"]},
    )


SAMPLE = (
    "The quick brown fox jumps over the lazy dog.\n\n"
    "Pack my box with five dozen liquor jugs.\n\n"
    "How vexingly quick daft zebras jump!\n\n"
    "Sphinx of black quartz, judge my vow."
)


# ===========================================================================
# SimpleTextChunker
# ===========================================================================

class TestSimpleTextChunker:

    @pytest.fixture
    def chunker(self):
        from pipeline.chunking.simple_chunker import SimpleTextChunker
        return SimpleTextChunker(chunk_size=50, overlap=10)

    def test_non_empty_input_produces_chunks(self, chunker):
        chunks, texts = chunker.chunk(_make_part(SAMPLE))
        assert len(chunks) > 0
        assert len(texts) == len(chunks)

    def test_empty_input_produces_no_chunks(self, chunker):
        chunks, texts = chunker.chunk(_make_part(""))
        assert chunks == []
        assert texts == []

    def test_no_chunk_exceeds_chunk_size(self):
        from pipeline.chunking.simple_chunker import SimpleTextChunker
        size = 50
        chunker = SimpleTextChunker(chunk_size=size, overlap=0)
        _, texts = chunker.chunk(_make_part("a" * 300))
        for t in texts:
            assert len(t) <= size

    def test_full_text_coverage_without_overlap(self):
        from pipeline.chunking.simple_chunker import SimpleTextChunker
        text = "x" * 200
        chunker = SimpleTextChunker(chunk_size=50, overlap=0)
        _, texts = chunker.chunk(_make_part(text))
        assert "".join(texts) == text

    def test_chunk_ids_are_deterministic(self, chunker):
        part = _make_part(SAMPLE)
        ids1 = [c.id for c in chunker.chunk(part)[0]]
        ids2 = [c.id for c in chunker.chunk(part)[0]]
        assert ids1 == ids2

    def test_chunk_ids_are_unique(self, chunker):
        chunks, _ = chunker.chunk(_make_part("y" * 500))
        ids = [c.id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_single_chunk_when_text_fits(self):
        from pipeline.chunking.simple_chunker import SimpleTextChunker
        chunker = SimpleTextChunker(chunk_size=200, overlap=0)
        chunks, texts = chunker.chunk(_make_part("short"))
        assert len(chunks) == 1
        assert texts[0] == "short"

    def test_metadata_contains_start_and_end(self, chunker):
        chunks, _ = chunker.chunk(_make_part("a" * 100))
        for c in chunks:
            assert "start" in c.metadata
            assert "end" in c.metadata

    def test_metadata_char_len(self, chunker):
        chunks, texts = chunker.chunk(_make_part(SAMPLE))
        for chunk, text in zip(chunks, texts):
            assert chunk.metadata["char_len"] == len(text)

    def test_rejects_overlap_gte_chunk_size(self):
        from pipeline.chunking.simple_chunker import SimpleTextChunker
        with pytest.raises(ValueError):
            SimpleTextChunker(chunk_size=10, overlap=10)
        with pytest.raises(ValueError):
            SimpleTextChunker(chunk_size=10, overlap=15)

    def test_chunk_text_field_matches_texts_list(self, chunker):
        chunks, texts = chunker.chunk(_make_part(SAMPLE))
        for chunk, text in zip(chunks, texts):
            assert chunk.text == text

    def test_chunk_device_id_propagated(self, chunker):
        part = _make_part(SAMPLE)
        chunks, _ = chunker.chunk(part)
        for c in chunks:
            assert c.device_id == part.device_id

    def test_chunk_source_path_propagated(self, chunker):
        part = _make_part(SAMPLE)
        chunks, _ = chunker.chunk(part)
        for c in chunks:
            assert c.source_path == part.source_path

    def test_chunk_indices_are_sequential(self, chunker):
        chunks, _ = chunker.chunk(_make_part("z" * 300))
        assert [c.index for c in chunks] == list(range(len(chunks)))

    def test_overlap_causes_extra_chunks(self):
        from pipeline.chunking.simple_chunker import SimpleTextChunker
        text = "a" * 100
        no_overlap = SimpleTextChunker(chunk_size=50, overlap=0)
        with_overlap = SimpleTextChunker(chunk_size=50, overlap=25)
        c1, _ = no_overlap.chunk(_make_part(text))
        c2, _ = with_overlap.chunk(_make_part(text))
        assert len(c2) > len(c1)


# ===========================================================================
# SentenceAwareChunker
# ===========================================================================

class TestSentenceAwareChunker:

    @pytest.fixture
    def chunker(self):
        from pipeline.chunking.sentence_chunker import SentenceAwareChunker
        return SentenceAwareChunker(max_chars=200, overlap_sentences=1, min_chars=0)

    def test_non_empty_produces_chunks(self, chunker):
        chunks, texts = chunker.chunk(_make_part(SAMPLE))
        assert len(chunks) > 0
        assert len(texts) == len(chunks)

    def test_empty_input_produces_no_chunks(self, chunker):
        chunks, texts = chunker.chunk(_make_part(""))
        assert chunks == []
        assert texts == []

    def test_chunk_ids_are_deterministic(self, chunker):
        part = _make_part(SAMPLE)
        ids1 = [c.id for c in chunker.chunk(part)[0]]
        ids2 = [c.id for c in chunker.chunk(part)[0]]
        assert ids1 == ids2

    def test_chunk_ids_are_unique(self, chunker):
        chunks, _ = chunker.chunk(_make_part(SAMPLE * 3))
        ids = [c.id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_no_chunk_exceeds_max_chars(self):
        from pipeline.chunking.sentence_chunker import SentenceAwareChunker
        max_chars = 80
        chunker = SentenceAwareChunker(max_chars=max_chars, overlap_sentences=0, min_chars=0)
        _, texts = chunker.chunk(_make_part(SAMPLE))
        for t in texts:
            assert len(t) <= max_chars, f"Chunk of len {len(t)} > max_chars={max_chars}: {t!r}"

    def test_single_paragraph_gives_one_chunk(self, chunker):
        text = "One short paragraph with no double newline."
        chunks, _ = chunker.chunk(_make_part(text))
        assert len(chunks) == 1

    def test_chunk_text_matches_texts_list(self, chunker):
        chunks, texts = chunker.chunk(_make_part(SAMPLE))
        for c, t in zip(chunks, texts):
            assert c.text == t

    def test_negative_overlap_rejected(self):
        from pipeline.chunking.sentence_chunker import SentenceAwareChunker
        with pytest.raises(ValueError):
            SentenceAwareChunker(overlap_sentences=-1)

    def test_metadata_has_sentence_count(self, chunker):
        chunks, _ = chunker.chunk(_make_part(SAMPLE))
        for c in chunks:
            assert "sentence_count" in c.metadata
            assert c.metadata["sentence_count"] >= 1

    def test_paragraph_breaks_respected(self, chunker):
        """Double newlines must always force a chunk boundary."""
        # Use distinct paragraphs so the similarity threshold doesn't merge them
        text = "\n\n".join(f"{'ABCDEFGHIJ'[i]* 50}" for i in range(5))
        chunks, _ = chunker.chunk(_make_part(text=text))
        assert len(chunks) >= 5

# ===========================================================================
# SemanticChunker (via DummyEmbeddingProvider — no GPU)
# ===========================================================================

class TestSemanticChunkerWithDummy:

    @pytest.fixture
    def chunker(self):
        from pipeline.chunking.semantic_chunker import SemanticChunker
        from pipeline.embeddings.dummy import DummyEmbeddingProvider
        return SemanticChunker(
            embedder=DummyEmbeddingProvider(dimension=384),
            max_chars=200,
            similarity_threshold=0.99,  # high threshold → many splits → robust test
        )

    def test_non_empty_produces_chunks(self, chunker):
        chunks, texts = chunker.chunk(_make_part(SAMPLE))
        assert len(chunks) > 0

    def test_empty_produces_no_chunks(self, chunker):
        chunks, texts = chunker.chunk(_make_part(""))
        assert chunks == []
        assert texts == []

    def test_deterministic(self, chunker):
        part = _make_part(SAMPLE)
        ids1 = [c.id for c in chunker.chunk(part)[0]]
        ids2 = [c.id for c in chunker.chunk(part)[0]]
        assert ids1 == ids2

    def test_unique_ids(self, chunker):
        chunks, _ = chunker.chunk(_make_part(SAMPLE))
        ids = [c.id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_no_chunk_exceeds_max_chars(self, chunker):
        _, texts = chunker.chunk(_make_part(SAMPLE))
        for t in texts:
            assert len(t) <= 200

    def test_text_field_matches_list(self, chunker):
        chunks, texts = chunker.chunk(_make_part(SAMPLE))
        for c, t in zip(chunks, texts):
            assert c.text == t
