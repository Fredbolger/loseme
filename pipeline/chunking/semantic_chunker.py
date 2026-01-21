from typing import List, Tuple
import numpy as np

from src.domain.models import Document, Chunk
from src.domain.embeddings import EmbeddingProvider
from src.domain.ids import make_chunk_id
#from pipeline.embeddings.sentence_transformer import (
#    SentenceTransformerEmbeddingProvider,
#)


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
        embedder: EmbeddingProvider,
        similarity_threshold: float = 0.75,
        max_chars: int = 1200,
    ):
        self.similarity_threshold = similarity_threshold
        self.max_chars = max_chars
        self.embedder = embedder

    def chunk(self, document: Document, text: str) -> Tuple[List[Chunk], List[str]]:
        units = self._split_paragraphs(text)
        if not units:
            return [], []
        
        embeddings = [self.embedder.embed_query(u) for u in units]

        chunks: List[Chunk] = []
        chunk_texts: List[str] = []

        buffer = units[0]
        buffer_len = len(buffer)
        index = 0

        for i in range(1, len(units)):
            sim = float(np.dot(embeddings[i - 1], embeddings[i]))

            if (
                sim >= self.similarity_threshold
                and buffer_len + len(units[i]) <= self.max_chars
            ):
                buffer += "\n\n" + units[i]
                buffer_len += len(units[i])
            else:
                self._emit_chunk(
                    document, buffer, index, chunks, chunk_texts
                )
                index += 1
                buffer = units[i]
                buffer_len = len(buffer)

        self._emit_chunk(document, buffer, index, chunks, chunk_texts)
        return chunks, chunk_texts

    def _emit_chunk(
        self,
        document: Document,
        text: str,
        index: int,
        chunks: List[Chunk],
        chunk_texts: List[str],
    ):
        chunk_id = make_chunk_id(
            document_id=document.id,
            document_checksum=document.checksum,
            index=index,
        )

        chunks.append(
            Chunk(
                id=chunk_id,
                document_id=document.id,
                document_checksum=document.checksum,
                device_id=document.device_id,
                source_path=document.source_path,
                index=index,
                metadata={
                    "char_len": len(text),
                },
            )
        )
        chunk_texts.append(text)

    def _split_paragraphs(self, text: str) -> List[str]:
        return [
            p.strip()
            for p in text.split("\n\n")
            if p.strip()
        ]

