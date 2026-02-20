from src.core.config import CHUNKER_TYPE, EMBEDDING_MODEL, CROSS_ENCODER_MODEL, VECTOR_STORAGE 

import logging
logger = logging.getLogger(__name__)

def build_chunker():
    embedder = build_embedding_provider()

    if CHUNKER_TYPE == "semantic":
        from pipeline.chunking.semantic_chunker import SemanticChunker
        return SemanticChunker(embedder=embedder)

    from pipeline.chunking.simple_chunker import SimpleTextChunker
    return SimpleTextChunker()

def build_embedding_provider():
    if EMBEDDING_MODEL.startswith("sentence-transformer:"):
        from pipeline.embeddings.sentence_transformer import SentenceTransformerEmbeddingProvider
        logger.info(f"Using SentenceTransformer embedding model: {EMBEDDING_MODEL}")
        model = EMBEDDING_MODEL.split(":", 1)[1]
        return SentenceTransformerEmbeddingProvider(model)
    elif EMBEDDING_MODEL == "nomic-ai/nomic-embed-text-v1":
        from pipeline.embeddings.nomic import NomicEmbeddingProvider
        logger.info(f"Using Nomic embedding model: {EMBEDDING_MODEL}")
        return NomicEmbeddingProvider()
    elif EMBEDDING_MODEL == "bge-m3":
        from pipeline.embeddings.bgem3 import BGEM3EmbeddingProvider
        logger.info(f"Using BGEM3 embedding model: {EMBEDDING_MODEL}")
        return BGEM3EmbeddingProvider()

    raise ValueError(f"Unknown embedding model {EMBEDDING_MODEL}")

def build_cross_encoding_provider(model_name: str):
    return CrossEncoderEmbeddingProvider(model_name)

def build_vector_store(client):
    if VECTOR_STORAGE == "in-memory":
        from storage.vector_db.in_memory import InMemoryVectorStore
        return InMemoryVectorStore(client)
    elif VECTOR_STORAGE == "qdrant":
        from storage.vector_db.qdrant_store import QdrantVectorStore
        return QdrantVectorStore(client)
    elif VECTOR_STORAGE == "qdrant-hybrid":
        # Hybrid storage only makes sense with a hybrid embedding model
        if EMBEDDING_MODEL not in ["bge-m3"]: 
            raise ValueError("Qdrant hybrid storage requires 'hybrid' embedding model")
        from storage.vector_db.qdrant_store_hybrid import QdrantVectorStoreHybrid
        return  QdrantVectorStoreHybrid(client)

    raise ValueError(f"Unknown vector storage type {VECTOR_STORAGE}")
