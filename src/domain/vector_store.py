from abc import ABC, abstractmethod
from typing import List, Tuple
from .models import Chunk

class VectorStore(ABC):
    """
    Abstract interface for storing embeddings and associated metadata.
    Supports storing vectors, querying by vector similarity, and incremental updates.
    """

    @abstractmethod
    def add_vectors(self, chunks: List[Chunk], vectors: List[List[float]]) -> None:
        """Add chunks and their embeddings to the vector store."""
        pass

    @abstractmethod
    def query(self, vector: List[float], top_k: int = 10) -> List[Tuple[Chunk, float]]:
        """Return top_k chunks most similar to the given vector, with similarity scores."""
        pass

    @abstractmethod
    def remove_chunks(self, chunk_ids: List[str]) -> None:
        """Remove chunks by ID from the store."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all vectors from the store."""
        pass

    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimensionality the store expects."""
        pass

