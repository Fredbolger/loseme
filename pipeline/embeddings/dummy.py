# pipeline/embeddings/dummy.py
from typing import List
import hashlib

class DummyEmbeddingProvider:
    """
    Deterministic embedding provider for Phase 1.
    Converts text into a fixed-size vector using hashing.
    No ML dependencies, stable across runs.
    """

    def __init__(self, dimension: int = 384):
        self._dimension = dimension

    def dimension(self) -> int:
        return self._dimension

    def embed(self, text: str) -> List[float]:
        if not text:
            return [0.0] * self._dimension

        # Create a stable hash of the text
        digest = hashlib.sha256(text.encode("utf-8")).digest()

        # Expand hash bytes into floats deterministically
        vector = [0.0] * self._dimension
        for i in range(self._dimension):
            byte = digest[i % len(digest)]
            # map byte (0-255) to roughly [-1, 1]
            vector[i] = (byte / 127.5) - 1.0

        return vector
