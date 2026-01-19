from typing import List
from sentence_transformers import SentenceTransformer
from src.domain.embeddings import EmbeddingProvider

class NomicEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_name: str = "nomic-ai/nomic-embed-text-v1"):
        self._model = SentenceTransformer(
            model_name,
            trust_remote_code=True,
        )

    def embed_document(self, text: str) -> List[float]:
        annotated_text = "search_document: " + text
        return self._model.encode(
            annotated_text,
            normalize_embeddings=True,
        ).tolist()

    def embed_query(self, text: str) -> List[float]:
        annotated_text = "search_query: " + text
        return self._model.encode(
            annotated_text,
            normalize_embeddings=True,
        ).tolist()

    def dimension(self) -> int:
        return self._model.get_sentence_embedding_dimension()

