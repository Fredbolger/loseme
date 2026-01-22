import hashlib
from src.domain.models import Document
from src.domain.ids import make_logical_document_id
from pipeline.chunking.simple_chunker import SimpleTextChunker
from pipeline.chunking.semantic_chunker import SemanticChunker
from pipeline.embeddings.dummy import DummyEmbeddingProvider

def test_chunk_ids_deterministic_simple_chunker():
    text = "abcdef"
    checksum = hashlib.sha256(text.encode()).hexdigest()
    doc_id = make_logical_document_id(text)

    doc = Document(
        id=doc_id,
        checksum=checksum,
        source_type="filesystem",
        source_id="src",
        device_id="dev",
        source_path="/x",
        text="",
        docker_path="/y",
    )

    chunker = SimpleTextChunker(chunk_size=3, overlap=0)
    ids1 = [c.id for c in chunker.chunk(doc, text)[0]]
    ids2 = [c.id for c in chunker.chunk(doc, text)[0]]

    assert ids1 == ids2

def test_chunk_ids_deterministic_semantic_chunker():
    text = (
        "This is a test. This is only a test. But it needs to be long enough "
        "to create multiple chunks. Let's add some more text to ensure that "
        "happens. Semantic chunking is interesting!"
    )
    max_chars = 50
    assert len(text) > max_chars

    checksum = hashlib.sha256(text.encode()).hexdigest()
    doc_id = make_logical_document_id(text)

    doc = Document(
        id=doc_id,
        checksum=checksum,
        source_type="filesystem",
        source_id="src",
        device_id="dev",
        source_path="/x",
        text="",
        docker_path="/y",
    )

    embedder = DummyEmbeddingProvider()
    chunker = SemanticChunker(
        similarity_threshold=0.5,
        max_chars=max_chars,
        embedder=embedder,
    )

    ids1 = [c.id for c in chunker.chunk(doc, text)[0]]
    ids2 = [c.id for c in chunker.chunk(doc, text)[0]]

    assert ids1 == ids2
