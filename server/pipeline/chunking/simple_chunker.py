from typing import List, Tuple

from loseme_core.models import Chunk, DocumentPart
from loseme_core.ids import make_chunk_id


class SimpleTextChunker:
    """
    Deterministic, simple text chunker.
    Splits text into fixed-size chunks with overlap.

    Note: chunks may split mid-word/mid-sentence. For semantic quality
    prefer SentenceAwareChunker or SemanticChunker. Use this for fast
    ingestion or as a baseline.
    """

    name = "simple"
    version = "1.0"

    def __init__(self, chunk_size: int = 1000, overlap: int = 100):
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, part: DocumentPart) -> Tuple[List[Chunk], List[str]]:
        if not part.text:
            return [], []

        chunks = []
        chunk_texts = []
        start = 0
        index = 0
        step = self.chunk_size - self.overlap

        while start < len(part.text):
            end = start + self.chunk_size
            chunk_text = part.text[start:end]

            chunk_id = make_chunk_id(
                document_part_id=part.document_part_id,
                document_checksum=part.checksum,
                index=index,
            )

            chunks.append(
                Chunk(
                    id=chunk_id,
                    source_type=part.source_type,
                    source_path=part.source_path,
                    document_part_id=part.document_part_id,
                    document_checksum=part.checksum,
                    device_id=part.device_id,
                    unit_locator=part.unit_locator,
                    index=index,
                    text=chunk_text,
                    metadata={
                        "start": start,
                        "end": min(end, len(part.text)),
                        "char_len": len(chunk_text),
                    },
                )
            )
            chunk_texts.append(chunk_text)

            index += 1
            start += step

        return chunks, chunk_texts
