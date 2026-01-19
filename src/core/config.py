import os

CHUNKER_TYPE = os.getenv("LOSEME_CHUNKER", "simple")  # simple | semantic
EMBEDDING_MODEL = os.getenv(
    "LOSEME_EMBEDDING_MODEL",
    "sentence-transformer:all-MiniLM-L6-v2",
)

