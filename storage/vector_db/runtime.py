from storage.vector_db.in_memory import InMemoryVectorStore
from pipeline.embeddings.dummy import DummyEmbeddingProvider

_embedding = DummyEmbeddingProvider()
_store = InMemoryVectorStore(dimension=_embedding.dimension())

def get_vector_store():
    return _store

def get_embedding_provider():
    return _embedding

