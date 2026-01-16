from typing import List, Tuple
import math

from src.domain.models import Chunk
from storage.vector_db.base import VectorStore


class InMemoryVectorStore(VectorStore):
    """
    Minimal in-memory vector store.
    Intended for Phase 1 end-to-end validation only.
    """

    def __init__(self, dimension: int):
        self._dimension = dimension
        self._data: List[Tuple[Chunk, List[float]]] = []

    def add(self, chunk: Chunk, vector: List[float]) -> None:
        """
        Adds a chunk and its vector to the store.
        """
        if len(vector) != self._dimension:
            raise ValueError(
                f"Vector dimension mismatch: expected {self._dimension}, "
                f"got {len(vector)}"
            )

        # Replace if chunk with same ID already exists
        self._data = [(c, v) for c, v in self._data if c.id != chunk.id]
        self._data.append((chunk, vector))

    def search(
        self, 
        query_vector: List[float], 
        top_k: int
    ) -> List[Tuple[Chunk, float]]:
        """
        Search for the top_k most similar chunks.
        
        Returns:
            List of (chunk, score) tuples ordered by descending similarity
        """
        if len(query_vector) != self._dimension:
            raise ValueError(
                f"Query vector dimension mismatch: expected {self._dimension}, "
                f"got {len(query_vector)}"
            )

        scored = []
        for chunk, vector in self._data:
            score = self._cosine_similarity(query_vector, vector)
            scored.append((chunk, score))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def clear(self) -> None:
        """
        Clears the vector store.
        """
        self._data.clear()
    
    def dimension(self) -> int:
        return self._dimension
