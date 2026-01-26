from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from .models import Chunk

class EmbeddingOutput(BaseModel):
    dense: Optional[List[float]] = None
    sparse: Optional[Dict[int, float]] = None
    colbert_vec: Optional[List[List[float]]] = None
    extras: Dict[str, Any] = {}

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
    def embed_query(self, text: str) -> EmbeddingOutput:
        """Embed a search query (query-time)."""
