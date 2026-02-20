# pipeline/chunking/simple_chunker.py
from typing import List, Tuple
from src.sources.base.models import Document, Chunk, DocumentPart
from src.core.ids import make_chunk_id

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

    def chunk(self, part: DocumentPart) -> Tuple[List[Chunk], List[str]]:

        chunks = []
        chunk_texts = []
        start = 0
        index = 0

        while start < len(part.text):
            end = start + self.chunk_size
            chunk_text = part.text[start:end]

            chunk_id = make_chunk_id(
                document_part_id=part.document_part_id,
                document_checksum=part.checksum,
                index=index,
            )

            chunk_texts.append(chunk_text)
            chunks.append(
                Chunk(
                    id=chunk_id,
                    source_type=part.source_type,
                    document_part_id=part.document_part_id,
                    document_checksum=part.checksum,
                    device_id=part.device_id,
                    source_path=part.source_path,
                    unit_locator=part.unit_locator,
                    index=index,
                    content=chunk_text,
                    metadata={
                        "start": start,
                        "end": min(end, len(part.text)),
                    },
                )
            )

            index += 1
            start = end - self.overlap

        return (chunks, chunk_texts)
    
    """
    def chunk_multipart(self, document: Document, texts: List[str], unit_locators: List[str]) -> (List[Chunk], List[str]):
        all_chunks = []
        all_texts = []

        for text, unit_locator in zip(texts, unit_locators):
            chunks, chunk_texts = self.chunk(document, text, unit_locator)
            all_chunks.extend(chunks)
            all_texts.extend(chunk_texts)

        return all_chunks, all_texts
    """
