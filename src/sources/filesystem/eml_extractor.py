import email
from email.policy import default
from src.sources.base.extractor import DocumentExtractor, DocumentExtractionResult
from src.sources.base.registry import extractor_registry
from pathlib import Path
from typing import List, Dict, Any
from bs4 import BeautifulSoup
import logging 

logger = logging.getLogger(__name__)

def eml_to_text(eml_str: str) -> str:
    """Extract plain text from an .eml file."""
    msg = email.message_from_string(eml_str, policy=default)
    text_parts = []

    for part in msg.walk():
        content_type = part.get_content_type()
        if content_type == "text/plain":
            text_parts.append(part.get_payload(decode=True).decode(errors="ignore"))
        elif content_type == "text/html":
            html = part.get_payload(decode=True).decode(errors="ignore")
            text_parts.append(BeautifulSoup(html, "html.parser").get_text("\n", strip=True))

    return "\n".join(text_parts)

class EMLExtractor(DocumentExtractor):
    name: str = "eml"
    priority: int = 1
    supported_mime_types: set[str] = {"message/rfc822"}
    version: str = "0.1"

    def can_extract(self, path: Path) -> bool:
        return path.suffix.lower() == ".eml"

    def can_extract_content_type(self, content_type: str) -> bool:
        return content_type.lower() in self.supported_mime_types

    def can_extract_bytes(self, file_bytes: bytes) -> bool:
        try:
            text = file_bytes.decode("utf-8", errors="ignore")
            # Check if the text looks like an email (e.g., contains headers like "From:", "Subject:", etc.)
            return "From:" in text and "Subject:" in text
        except UnicodeDecodeError:
            return False

    def extract_from_bytes(self, file_bytes: bytes) -> DocumentExtractionResult:
        eml_str = file_bytes.decode("utf-8", errors="ignore")
        extracted_text = eml_to_text(eml_str)

        # Extract metadata from the email headers
        msg = email.message_from_string(eml_str, policy=default)
        metadata = {
            "from": msg.get("From", ""),
            "to": msg.get("To", ""),
            "subject": msg.get("Subject", ""),
            "date": msg.get("Date", ""),
            "cc": msg.get("Cc", ""),
            "bcc": msg.get("Bcc", ""),
        }

        return DocumentExtractionResult(
            texts=[extracted_text],
            content_types=["message/rfc822"],
            metadata=[metadata],
            unit_locators=[],  # No unit locators available when extracting from bytes
            extractor_names=[self.name],
            extractor_versions=[self.version],
        )

    def extract(self, path: Path) -> DocumentExtractionResult:
        logger.debug(f"Extracting .eml file from path: {path}")
        eml_str = path.read_text(encoding="utf-8", errors="ignore")
        extracted_text = eml_to_text(eml_str)

        # Extract metadata from the email headers
        msg = email.message_from_string(eml_str, policy=default)
        metadata = {
            "filename": path.name,
            "suffix": path.suffix,
            "from": msg.get("From", ""),
            "to": msg.get("To", ""),
            "subject": msg.get("Subject", ""),
            "date": msg.get("Date", ""),
            "cc": msg.get("Cc", ""),
            "bcc": msg.get("Bcc", ""),
        }
        logger.debug(f"Extracted metadata: {metadata}")

        return DocumentExtractionResult(
            texts=[extracted_text],
            content_types=["message/rfc822"],
            metadata=[metadata],
            unit_locators=[f"filesystem:{path.resolve()}"],
            extractor_names=[self.name],
            extractor_versions=[self.version],
        )

# Register the extractor
extractor_registry.register_extractor(EMLExtractor())

