from pathlib import Path
from src.sources.base.extractor import DocumentExtractor, DocumentExtractionResult
from src.sources.base.registry import extractor_registry
from pypdf import PdfReader
import logging

logger = logging.getLogger(__name__)

class PDFExtractor(DocumentExtractor):
    priority: int = 20
    name: str = "pdf"
    supported_mime_types: set[str] = {"application/pdf"}
    version: str = "0.1"

    def can_extract(self, path: Path) -> bool:
        return path.suffix.lower() == ".pdf"

    def can_extract_bytes(self, file_bytes: bytes) -> bool:
        # Simple check if bytes math ['application/pdf' magic number
        return file_bytes[:4] == b"%PDF"
    
    def can_extract_content_type(self, content_type: str) -> bool:
        return content_type.lower() == "application/pdf"

    def extract(self, path: Path) -> DocumentExtractionResult:

        reader = PdfReader(str(path))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"

        return DocumentExtractionResult(
            texts=[text],
            content_types=["application/pdf"],
            metadata=[{
                "filename": path.name,
                "suffix": path.suffix,
                "num_pages": len(reader.pages),
            }],
            unit_locators=[f"filesystem:{path.resolve()}"],
            extractor_names=[self.name],
            extractor_versions=[self.version],
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
                texts=[""],
                content_types=["application/pdf"],
                metadata=[{
                    "error": "Failed to decrypt PDF",
                }],
                unit_locators=["memory:pdf"],
                extractor_names=[self.name],
                extractor_versions=[self.version],
            )

        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"

        return DocumentExtractionResult(
            texts=[text],
            content_types=["application/pdf"],
            metadata=[{
                "num_pages": len(reader.pages),
            }],
            unit_locators=[],
            extractor_names=[self.name],
            extractor_versions=[self.version],
        )

# Register the PDFExtractor in the global extractor registry
extractor_registry.register_extractor(PDFExtractor())
