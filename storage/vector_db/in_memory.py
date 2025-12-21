# storage/vector_db/in_memory.py
from typing import List, Tuple
import math

from src.domain.models import Chunk

class InMemoryVectorStore:
    """
    Minimal in-memory vector store.
    Intended for Phase 1 end-to-end validation only.
    """

    def __init__(self, dimension: int):
        self.dimension = dimension
        self._vectors: List[Tuple[str, List[float], dict]] = []

    def add(self, chunk: Chunk, vector: List[float]) -> None:
        if len(vector) != self.dimension:
            raise ValueError("Vector dimension mismatch")

        self._vectors.append(
            (
                chunk.id,
                vector,
                {
                    "document_id": chunk.document_id,
                    **chunk.metadata,
                },
            )
        )

    def query(self, query_vector: List[float], top_k: int = 5):
        if len(query_vector) != self.dimension:
            raise ValueError("Query vector dimension mismatch")

        scored = []
        for chunk_id, vector, metadata in self._vectors:
            score = self._cosine_similarity(query_vector, vector)
            scored.append((chunk_id, score, metadata))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

