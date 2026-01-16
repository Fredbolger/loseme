import hashlib
from src.domain.models import Document
from src.domain.ids import make_logical_document_id
from pipeline.chunking.simple_chunker import SimpleTextChunker

def test_chunk_ids_deterministic():
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
    )

    chunker = SimpleTextChunker(chunk_size=3, overlap=0)
    ids1 = [c.id for c in chunker.chunk(doc, text)[0]]
    ids2 = [c.id for c in chunker.chunk(doc, text)[0]]

    assert ids1 == ids2

