# pipeline/chunking/simple_chunker.py
from typing import List
from src.domain.models import Document, Chunk
import hashlib

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

    def chunk(self, document: Document, text: str) -> List[Chunk]:
        chunks: List[Chunk] = []
        start = 0
        index = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end]

            # deterministic chunk id
            raw_id = f"{document.id}:{index}:{chunk_text}".encode("utf-8")
            chunk_id = hashlib.sha256(raw_id).hexdigest()

            chunks.append(
                Chunk(
                    id=chunk_id,
                    document_id=document.id,
                    content=chunk_text,
                    metadata={
                        "chunk_index": index,
                        "start": start,
                        "end": min(end, len(text)),
                    },
                )
            )

            index += 1
            start = end - self.overlap

        return chunks
