from abc import ABC, abstractmethod
from typing import Iterable
from src.domain.models import Chunk

class VectorStore(ABC):

    @abstractmethod
    def add(self, chunk: Chunk, vector: list[float]) -> None:
        ...

    @abstractmethod
    def search(self, query_vector: list[float], top_k: int) -> list[Chunk]:
        ...

    @abstractmethod
    def clear(self) -> None:
        ...

