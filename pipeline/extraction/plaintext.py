from pathlib import Path
from pipeline.extraction.base import DocumentExtractor, DocumentExtractionResult
import os
 
class PlainTextExtractor(DocumentExtractor):
    priority: int = 10
    name: str = "plaintext"

    def can_extract(self, path: Path) -> bool:
        return path.suffix.lower() in {".txt", ".md", ".rst"}
    
    def can_extract_bytes(self, file_bytes: bytes) -> bool:
        # We won't implement byte extraction for plain text files
        return False

    def extract(self, path: Path) -> DocumentExtractionResult:
        # if we are running inside Docker, we need to remove the SOURCE_ROOT prefix
        text = path.read_text(encoding="utf-8", errors="ignore")
        return DocumentExtractionResult(
            text=text,
            content_type="text/plain",
            metadata={
                "filename": path.name,
                "suffix": path.suffix,
            },
        )

