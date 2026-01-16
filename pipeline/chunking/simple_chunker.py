# pipeline/chunking/simple_chunker.py
from typing import List
from src.domain.models import Document, Chunk
from src.domain.ids import make_chunk_id

class SimpleTextChunker:
    """
    Deterministic, simple text chunker.
    Splits text into fixed-size chunks with overlap.
    Suitable for Phase 1 validation of the pipeline.
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, document: Document, text: str) -> (List[Chunk], List[str]):
        chunks = []
        chunk_texts = []
        start = 0
        index = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end]

            chunk_id = make_chunk_id(
                document_id=document.id,
                document_checksum=document.checksum,
                index=index,
            )

            chunk_texts.append(chunk_text)
            chunks.append(
                Chunk(
                    id=chunk_id,
                    
                    document_id=document.id,
                    document_checksum=document.checksum,
                    device_id=document.device_id,
                    source_path=document.source_path,
                    index=index,
                    content=chunk_text,
                    metadata={
                        "start": start,
                        "end": min(end, len(text)),
                    },
                )
            )

            index += 1
            start = end - self.overlap

        return (chunks, chunk_texts)
