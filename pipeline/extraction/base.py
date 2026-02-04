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
    name: str = "base"
    priority: int = 0

    @abstractmethod
    def can_extract(self, path: Path) -> bool:
        """Return Tru if this extractor supports the file"""

    @abstractmethod
    def can_extract_bytes(self, file_bytes: bytes) -> bool:
        """Return True if this extractor supports the content type"""

    @abstractmethod
    def extract(self, path: Path) -> DocumentExtractionResult:
        """Extract canonical text + metadata"""

