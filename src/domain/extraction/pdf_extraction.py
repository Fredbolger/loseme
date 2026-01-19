from pathlib import Path
from src.domain.extraction.base import DocumentExtractor, DocumentExtractionResult
from pypdf import PdfReader

class PDFExtractor(DocumentExtractor):
    priority: int = 20

    def can_extract(self, path: Path) -> bool:
        return path.suffix.lower() == ".pdf"

    def extract(self, path: Path) -> DocumentExtractionResult:

        reader = PdfReader(str(path))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"

        return DocumentExtractionResult(
            text=text,
            content_type="application/pdf",
            metadata={
                "filename": path.name,
                "suffix": path.suffix,
                "num_pages": len(reader.pages),
            },
        )
