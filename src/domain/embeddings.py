from abc import ABC, abstractmethod
from typing import List
from .models import Chunk

class EmbeddingProvider(ABC):
    """
    Abstract interface for converting chunks into vector embeddings.
    Implementations can be local models, OpenAI API, or other vector providers.
    """

    @abstractmethod
    def embed(self, chunks: List[Chunk]) -> List[List[float]]:
        """Given a list of chunks, return a list of embeddings (vectors)."""
        pass

    @abstractmethod
    def embedding_dimension(self) -> int:
        """Return the dimensionality of the embeddings produced by this provider."""
        pass
