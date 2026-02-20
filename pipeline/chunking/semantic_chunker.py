from typing import List, Tuple
import numpy as np

from src.sources.base.models import Document, Chunk, DocumentPart
from src.core.wiring import build_embedding_provider
from src.core.ids import make_chunk_id



class SemanticChunker:
    """
    Embedding-based semantic chunker.

    Algorithm:
    1. Split text into base units (paragraphs)
    2. Embed each unit
    3. Merge adjacent units if cosine similarity >= threshold
    4. Enforce max_chars hard limit

    Deterministic, order-preserving, resumable-safe.
    """

    def __init__(
        self,
        embedder: build_embedding_provider(),
        similarity_threshold: float = 0.75,
        max_chars: int = 1200,
        ):
        self.similarity_threshold = similarity_threshold
        self.max_chars = max_chars
        self.embedder = embedder

    def chunk(self, part: DocumentPart) -> Tuple[List[Chunk], List[str]]:

        units = self._split_paragraphs(part.text)
        if not units:
            return [], []

        # Embed each unit
        embeddings = [self.embedder.embed_query(u) for u in units]

        chunks: List[Chunk] = []
        chunk_texts: List[str] = []

        buffer = units[0]
        buffer_len = len(buffer)
        index = 0

        for i in range(1, len(units)):
            # Extract dense vectors before computing similarity
            vec_prev = np.array(embeddings[i - 1].dense)
            vec_curr = np.array(embeddings[i].dense)
            sim = float(np.dot(vec_prev, vec_curr))

            if sim >= self.similarity_threshold and buffer_len + len(units[i]) <= self.max_chars:
                buffer += "\n\n" + units[i]
                buffer_len += len(units[i])
            else:
                self._emit_chunk(part, buffer, index, chunks, chunk_texts)
                index += 1
                buffer = units[i]
                buffer_len = len(buffer)

        # Emit last buffer
        self._emit_chunk(part, buffer, index, chunks, chunk_texts)
        return chunks, chunk_texts


    def _emit_chunk(
        self,
        document_part: DocumentPart,
        text: str,
        index: int,
        chunks: List[Chunk],
        chunk_texts: List[str],

    ):
        chunk_id = make_chunk_id(
            document_part_id=document_part.document_part_id,
            document_checksum=document_part.checksum,
            index=index,
        )

        chunks.append(
            Chunk(
                id=chunk_id,
                document_part_id=document_part.document_part_id,
                source_type=document_part.source_type,
                source_path=document_part.source_path,
                document_checksum=document_part.checksum,
                device_id=document_part.device_id,
                index=index,
                unit_locator=document_part.unit_locator,
                metadata={
                    "char_len": len(text),
                },
                text=text
            )
        )
        chunk_texts.append(text)

    def _split_paragraphs(self, text: str) -> List[str]:
        return [
            p.strip()
            for p in text.split("\n\n")
            if p.strip()
        ]
