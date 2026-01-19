from src.domain.extraction.registry import ExtractorRegistry
from src.domain.extraction.plaintext import PlainTextExtractor
from src.domain.extraction.pdf_extraction import PDFExtractor
from src.domain.extraction.thunderbird_extractor import ThunderbirdExtractor
from pipeline.chunking.simple_chunker import SimpleTextChunker
from pipeline.chunking.semantic_chunker import SemanticChunker
from pipeline.embeddings.sentence_transformer import SentenceTransformerEmbeddingProvider
from pipeline.embeddings.nomic import NomicEmbeddingProvider
from src.core.config import CHUNKER_TYPE, EMBEDDING_MODEL

import logging
logger = logging.getLogger(__name__)

def build_extractor_registry() -> ExtractorRegistry:
    return ExtractorRegistry(
        extractors=[
            PlainTextExtractor(),
            PDFExtractor(),
            ThunderbirdExtractor(),
            # As the project evolves, additional extractors can be registered here.
            # ImageOcrExtractor(),
        ]
    )

def build_chunker():
    embedder = build_embedding_provider()

    if CHUNKER_TYPE == "semantic":
        return SemanticChunker(embedder=embedder)

    return SimpleTextChunker()

def build_embedding_provider():
    if EMBEDDING_MODEL.startswith("sentence-transformer:"):
        logger.info(f"Using SentenceTransformer embedding model: {EMBEDDING_MODEL}")
        model = EMBEDDING_MODEL.split(":", 1)[1]
        return SentenceTransformerEmbeddingProvider(model)
    elif EMBEDDING_MODEL == "nomic-ai/nomic-embed-text-v1":
        logger.info(f"Using Nomic embedding model: {EMBEDDING_MODEL}")
        return NomicEmbeddingProvider()
    raise ValueError(f"Unknown embedding model {EMBEDDING_MODEL}")
