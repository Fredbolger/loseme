# pipeline/embeddings/dummy.py
from src.domain.embeddings import EmbeddingProvider, EmbeddingOutput
from src.domain.models import Chunk
from typing import List
import hashlib

class DummyEmbeddingProvider(EmbeddingProvider):
    """
    Deterministic embedding provider for Phase 1.
    Converts text into a fixed-size vector using hashing.
    No ML dependencies, stable across runs.
    """

    def __init__(self, dimension: int = 384):
        self._dimension = dimension

    def _embed_text(self, text: str) -> EmbeddingOutput:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        vec = [(digest[i % len(digest)] / 127.5) - 1.0 for i in range(self._dimension)]
        return EmbeddingOutput(dense=vec)

    def dimension(self) -> int:
        return self._dimension
    
    def embed_query(self, text: str) -> EmbeddingOutput:
        return EmbeddingOutput(dense=self._embed_text(text).dense)
