from pathlib import Path
from src.domain.extraction.base import DocumentExtractor, DocumentExtractionResult

class PlainTextExtractor(DocumentExtractor):
    priority: int = 10

    def can_extract(self, path: Path) -> bool:
        return path.suffix.lower() in {".txt", ".md", ".rst"}

    def extract(self, path: Path) -> DocumentExtractionResult:
        text = path.read_text(encoding="utf-8", errors="ignore")
        return DocumentExtractionResult(
            text=text,
            content_type="text/plain",
            metadata={
                "filename": path.name,
                "suffix": path.suffix,
            },
        )

