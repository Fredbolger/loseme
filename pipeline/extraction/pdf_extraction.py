from pathlib import Path
from pipeline.extraction.base import DocumentExtractor, DocumentExtractionResult
from pypdf import PdfReader
import logging

logger = logging.getLogger(__name__)

class PDFExtractor(DocumentExtractor):
    priority: int = 20
    name: str = "pdf"

    def can_extract(self, path: Path) -> bool:
        return path.suffix.lower() == ".pdf"

    def can_extract_bytes(self, file_bytes: bytes) -> bool:
        # Simple check if bytes math ['application/pdf' magic number
        return file_bytes[:4] == b"%PDF"

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

    def extract_from_bytes(self, file_bytes: bytes) -> DocumentExtractionResult:
        from io import BytesIO
        
        reader = PdfReader(BytesIO(file_bytes))
        # test if the file is encrypted
        try:
            # try to iterate through pages to see if decryption is needed
            for _ in reader.pages:
                pass
        except Exception as e:
            logger.warning(f"Failed to decrypt PDF: {e}")
            return DocumentExtractionResult(
                text="",
                content_type="application/pdf",
                metadata={
                    "error": "Failed to decrypt PDF",
                },
            )

        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"

        return DocumentExtractionResult(
            text=text,
            content_type="application/pdf",
            metadata={
                "num_pages": len(reader.pages),
            },
        )
