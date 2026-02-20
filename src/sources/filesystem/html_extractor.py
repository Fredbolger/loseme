from pathlib import Path
from src.sources.base.extractor import DocumentExtractor, DocumentExtractionResult
from src.sources.base.registry import extractor_registry
import os
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def html_to_text_bs(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text("\n", strip=True)

class HTMLExtractor(DocumentExtractor):
    name: str = "html"
    priority: int = 5
    supported_mime_types: set[str] = {"text/html"}
    version: str = "0.1"

    def can_extract(self, path: Path) -> bool:
        return path.suffix.lower() in {".html", ".htm"}
    
    def can_extract_content_type(self, content_type: str) -> bool:
        return content_type.lower() in self.supported_mime_types
    
    def can_extract_bytes(self, file_bytes: bytes) -> bool:
        # Check if the bytes can be decoded as UTF-8 without errors and contain HTML tags
        try:
            text = file_bytes.decode("utf-8")
            return "<html" in text.lower() and "</html>" in text.lower()
        except UnicodeDecodeError:
            return False

    def extract_from_bytes(self, file_bytes: bytes) -> DocumentExtractionResult:
        text = file_bytes.decode("utf-8", errors="ignore")
        extracted_text = html_to_text_bs(text)
        return DocumentExtractionResult(
            texts=[extracted_text],
            content_types=["text/html"],
            metadata=[{}],  # No metadata available when extracting from bytes
            unit_locators=[],  # No unit locators available when extracting from bytes
            extractor_names=[self.name],
            extractor_versions=[self.version],
        )

    def extract(self, path: Path) -> DocumentExtractionResult:
        html = path.read_text(encoding="utf-8", errors="ignore")
        extracted_text = html_to_text_bs(html)
        return DocumentExtractionResult(
            texts=[extracted_text],
            content_types=["text/html"],
            metadata=[{
                "filename": path.name,
                "suffix": path.suffix,
            }],
            unit_locators=[f"filesystem:{path.resolve()}"],
            extractor_names=[self.name],
            extractor_versions=[self.version],
        )

extractor_registry.register_extractor(HTMLExtractor())
