from typing import List
from sentence_transformers import SentenceTransformer
from src.domain.embeddings import EmbeddingProvider, EmbeddingOutput

class NomicEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_name: str = "nomic-ai/nomic-embed-text-v1"):
        self._model = SentenceTransformer(
            model_name,
            revision="9cff80ccfaa78556e1f8883129e2fe70c9fd5e49",
            trust_remote_code=True,
        )

    def embed_document(self, text: str) -> EmbeddingOutput:
        annotated_text = "search_document: " + text
        embedding = self._model.encode(
            annotated_text,
            normalize_embeddings=True,
        ).tolist()
        return EmbeddingOutput(dense=embedding)

    def embed_query(self, text: str) -> EmbeddingOutput:
        annotated_text = "search_query: " + text
        embedding = self._model.encode(
            annotated_text,
            normalize_embeddings=True,
        ).tolist()
        return EmbeddingOutput(dense=embedding)

    def dimension(self) -> int:
        return self._model.get_sentence_embedding_dimension()

