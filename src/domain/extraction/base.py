from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

class DocumentExtractionResult:
    def __init__(
        self,
        text: str,
        metadata: dict,
        content_type: str,
    ):
        self.text = text
        self.metadata = metadata
        self.content_type = content_type


class DocumentExtractor(ABC):
    @abstractmethod
    def can_extract(self, path: Path) -> bool:
        """Return True if this extractor supports the file"""

    @abstractmethod
    def extract(self, path: Path) -> DocumentExtractionResult:
        """Extract canonical text + metadata"""

