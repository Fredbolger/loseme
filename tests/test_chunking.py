import hashlib
from src.sources.base.models import Document, DocumentPart
from src.core.ids import make_logical_document_part_id
from pipeline.chunking.simple_chunker import SimpleTextChunker
from pipeline.chunking.semantic_chunker import SemanticChunker
from pipeline.embeddings.dummy import DummyEmbeddingProvider

def test_chunk_ids_deterministic_simple_chunker():
    text = "abcdef"
    checksum = hashlib.sha256(text.encode()).hexdigest()
    source_instance_id = "src"
    doc_id = make_logical_document_part_id(source_instance_id=source_instance_id, unit_locator="filesystem:/x")

    chunker = SimpleTextChunker(chunk_size=3, overlap=0)
    part = DocumentPart(text=text, 
                        document_part_id=doc_id,
                        checksum=checksum,
                        source_type="filesystem",
                        source_instance_id="src",
                        device_id="dev",
                        source_path="/x",
                        unit_locator="loc", 
                        content_type="text/plain", 
                        extractor_name="test", 
                        extractor_version="1.0")


    ids1 = [c.id for c in chunker.chunk(part)[0]]
    ids2 = [c.id for c in chunker.chunk(part)[0]]

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
    source_instance_id = "src"
    doc_id = make_logical_document_part_id(source_instance_id=source_instance_id, unit_locator="filesystem:/x")

    embedder = DummyEmbeddingProvider()
    chunker = SemanticChunker(
        similarity_threshold=0.5,
        max_chars=max_chars,
        embedder=embedder,
    )
    
    part = DocumentPart(text=text,
                        document_part_id=doc_id,
                        checksum=checksum,
                        source_type="filesystem",
                        source_instance_id="src",
                        device_id="dev",
                        source_path="/x",
                        unit_locator="loc", 
                        content_type="text/plain", 
                        extractor_name="test", 
                        extractor_version="1.0")
    
    ids1 = [c.id for c in chunker.chunk(part)[0]]
    ids2 = [c.id for c in chunker.chunk(part)[0]]

    assert ids1 == ids2
