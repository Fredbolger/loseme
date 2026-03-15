from abc import ABC, abstractmethod
from typing import Optional
from .models import PreviewResult
import logging

logger = logging.getLogger(__name__)


class PreviewGenerator(ABC):
    """
    Base class for all preview generators. Mirrors DocumentExtractor.

    Subclasses must set:
      name     : str   — unique identifier, e.g. "thunderbird_email"
      priority : int   — higher wins when multiple generators match
    """
    name: str = "base"
    priority: int = 0

    @abstractmethod
    def can_handle(self, source_type: str, doc_part: dict) -> bool:
        """Return True if this generator can preview this document part."""

    @abstractmethod
    def generate(self, doc_part: dict) -> PreviewResult:
        """Produce a PreviewResult for the given document part."""


class PreviewRegistry:
    def __init__(self):
        self._generators: list[PreviewGenerator] = []

    def register(self, generator: PreviewGenerator) -> None:
        self._generators.append(generator)
        self._generators.sort(key=lambda g: g.priority, reverse=True)
        logger.debug(f"Registered preview generator: {generator.name}")

    def get_generator(self, source_type: str, doc_part: dict) -> Optional[PreviewGenerator]:
        for g in self._generators:
            if g.can_handle(source_type, doc_part):
                logger.debug(f"Using preview generator: {g.name}")
                return g
        return None

    def list_generators(self) -> list[str]:
        return [g.name for g in self._generators]


# Singleton - import this everywhere, like extractor_registry
preview_registry = PreviewRegistry()
