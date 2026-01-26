from typing import List
from sentence_transformers import SentenceTransformer

from src.domain.embeddings import EmbeddingProvider, EmbeddingOutput
from src.domain.models import Chunk

class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self._dimension = self.model.get_sentence_embedding_dimension()

    def dimension(self) -> int:
        return self._dimension

    def embed_query(self, text: str) -> EmbeddingOutput:
        embedding = self.model.encode(
            text,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        output = EmbeddingOutput(dense=embedding.tolist())
