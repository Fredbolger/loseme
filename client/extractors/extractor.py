from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

class DocumentExtractionResult(BaseModel):
    texts: list[str]
    metadata: list[dict]
    unit_locators: list[str]
    content_types: list[str]
    extractor_names: list[str]
    extractor_versions: list[str]
    is_multipart: bool = Field(default=False)

    def text(self) -> str:
        """
        If the extracted result is single-part, return the text directly.
        If it's multi-part, throw an error to force the caller to handle the multiple parts explicitly.
        """
        if self.is_multipart:
            raise ValueError("This extraction result contains multiple parts. Use the 'texts' attribute to access all parts.")
        return self.texts[0]

    def content_type(self) -> str:
        """
        If the extracted result is single-part, return the content type directly.
        If it's multi-part, throw an error to force the caller to handle the multiple parts explicitly.
        """
        if self.is_multipart:
            raise ValueError("This extraction result contains multiple parts. Use the 'content_types' attribute to access all parts.")
        return self.content_types[0]

    def metadata(self) -> dict:
        """
        If the extracted result is single-part, return the metadata directly.
        If it's multi-part, throw an error to force the caller to handle the multiple parts explicitly.
        """
        if self.is_multipart:
            raise ValueError("This extraction result contains multiple parts. Use the 'metadata' attribute to access all parts.")
        return self.metadata[0]

    def extractor_name(self) -> str:
        """
        If the extracted result is single-part, return the extractor name directly.
        If it's multi-part, throw an error to force the caller to handle the multiple parts explicitly.
        """
        if self.is_multipart:
            raise ValueError("This extraction result contains multiple parts. Use the 'extractor_names' attribute to access all parts.")
        return self.extractor_names[0]

    def extractor_version(self) -> str:
        """
        If the extracted result is single-part, return the extractor version directly.
        If it's multi-part, throw an error to force the caller to handle the multiple parts explicitly.
        """
        if self.is_multipart:
            raise ValueError("This extraction result contains multiple parts. Use the 'extractor_versions' attribute to access all parts.")
        return self.extractor_versions[0]
    



class DocumentExtractor(ABC):
    name: str = "base"
    priority: int = 0
    supported_mime_types: Optional[set[str]] = None
    version: str
    registry = None  # This will be set (if needed) when the extractor is registered in the registry

    @abstractmethod
    def can_extract(self, path: Path) -> bool:
        """Return Tru if this extractor supports the file"""

    @abstractmethod
    def can_extract_bytes(self, file_bytes: bytes) -> bool:
        """Return True if this extractor supports the content type"""

    @abstractmethod
    def extract(self, path: Path) -> DocumentExtractionResult:
        """Extract canonical text + metadata"""

