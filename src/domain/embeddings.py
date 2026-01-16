from abc import ABC, abstractmethod
from typing import List
from .models import Chunk

class EmbeddingProvider(ABC):
    """
    Abstract interface for converting chunks into vector embeddings.
    Implementations can be local models, OpenAI API, or other vector providers.
    """
    
    @abstractmethod
    def dimension(self) -> int:
        """Return the dimensionality of the embeddings produced by this provider."""
        pass

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Embed a search query (query-time)."""
