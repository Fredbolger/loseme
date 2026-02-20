from pathlib import Path
from src.sources.base.extractor import DocumentExtractor, DocumentExtractionResult
from src.sources.base.registry import extractor_registry
import os
 
class PlainTextExtractor(DocumentExtractor):
    priority: int = 10
    name: str = "plaintext"
    supported_mime_types: set[str] = {"text/plain", "text/markdown"}
    version: str = "0.1"

    def can_extract(self, path: Path) -> bool:
        return path.suffix.lower() in {".txt", ".md", ".rst"}
   
    def can_extract_content_type(self, content_type: str) -> bool:
        return content_type.lower() in self.supported_mime_types

    def can_extract_bytes(self, file_bytes: bytes) -> bool:
        # Check if the bytes can be decoded as UTF-8 without errors
        try:
            file_bytes.decode("utf-8")
            return True
        except UnicodeDecodeError:
            return False

    def extract_from_bytes(self, file_bytes: bytes) -> DocumentExtractionResult:
        text = file_bytes.decode("utf-8", errors="ignore")
        return DocumentExtractionResult(
            texts=[text],
            content_types=["text/plain"],
            metadata=[{}],  # No metadata available when extracting from bytes
            unit_locators=[],  # No unit locators available when extracting from bytes
            extractor_names=[self.name],
            extractor_versions=[self.version],
        )
    def extract(self, path: Path) -> DocumentExtractionResult:
        # if we are running inside Docker, we need to remove the SOURCE_ROOT prefix
        text = path.read_text(encoding="utf-8", errors="ignore")
        return DocumentExtractionResult(
            texts=[text],
            content_types=["text/plain"],
            metadata=[{
                "filename": path.name,
                "suffix": path.suffix,
            }],
            unit_locators=[f"filesystem:{path.resolve()}"],
            extractor_names=[self.name],
            extractor_versions=[self.version],
        )

extractor_registry.register_extractor(PlainTextExtractor())
