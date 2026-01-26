from pathlib import Path
from pipeline.extraction.base import DocumentExtractor, DocumentExtractionResult
import os
 
SOURCE_ROOT = os.getenv("LOSEME_SOURCE_ROOT_HOST")

if SOURCE_ROOT is None:
    raise RuntimeError("LOSEME_SOURCE_ROOT_HOST environment variable is not set")

class PlainTextExtractor(DocumentExtractor):
    priority: int = 10

    def can_extract(self, path: Path) -> bool:
        return path.suffix.lower() in {".txt", ".md", ".rst"}

    def extract(self, path: Path) -> DocumentExtractionResult:
        # if we are running inside Docker, we need to remove the SOURCE_ROOT prefix
        if Path("/.dockerenv").exists():
            try:
                relative_path = path.relative_to(SOURCE_ROOT)
                path = Path("/") / relative_path
            except ValueError:
                # path is not under SOURCE_ROOT, do nothing
                pass
        text = path.read_text(encoding="utf-8", errors="ignore")
        return DocumentExtractionResult(
            text=text,
            content_type="text/plain",
            metadata={
                "filename": path.name,
                "suffix": path.suffix,
            },
        )

