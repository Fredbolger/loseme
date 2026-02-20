import os

CHUNKER_TYPE = os.getenv("LOSEME_CHUNKER", "simple")  # simple | semantic
EMBEDDING_MODEL = os.getenv(
    "LOSEME_EMBEDDING_MODEL",
    "sentence-transformer:all-MiniLM-L6-v2",
)

CROSS_ENCODER_MODEL = os.getenv(
    "LOSEME_CROSS_ENCODER_MODEL",
    "cross-encoder/ms-marco-MiniLM-L-6-v2",
)

VECTOR_STORAGE = os.getenv(
        "LOSEME_VECTOR_STORAGE", "qdrant"
        )

USE_CUDA = os.getenv("LOSEME_USE_CUDA", "false").lower() 
