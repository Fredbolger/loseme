import email
from email.policy import default
from email.header import decode_header, make_header
from email.message import Message
from src.sources.base.extractor import DocumentExtractor, DocumentExtractionResult
from src.sources.base.registry import extractor_registry
from pathlib import Path
from typing import List, Optional
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def _safe_get_header(message, header, default=""):
    """Get a raw header value without triggering strict policy parsing."""
    raw = message._headers  # list of (name, value) tuples
    for name, value in raw:
        if name.lower() == header.lower():
            return value.strip()
    return default

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
            return "From:" in text and "Subject:" in text
        except UnicodeDecodeError:
            return False

    def _extract_part(self, part: Message) -> Optional[DocumentExtractionResult]:
        """
        Extract a single non-multipart MIME part using the appropriate registry extractor.
        Returns None for parts that should be skipped entirely (multipart containers,
        encrypted parts). Returns an empty-text result for unsupported content types
        so the part is still recorded for future reprocessing.
        """
        if part.is_multipart():
            logger.debug("Skipping multipart container in _extract_part")
            return None

        if part.get_content_type() == "application/pkcs7-mime":
            logger.debug("Skipping encrypted part in _extract_part")
            return None

        content_type = part.get_content_type()
        disposition = part.get_content_disposition() or ""
        filename = part.get_filename() or ""

        if content_type == "text/plain" and disposition not in ("attachment",):
            extractor = self.registry.get_extractor("plaintext")
            if extractor is None:
                raise ValueError("Plain text extractor not found in registry")
            return extractor.extract_from_bytes(part.get_payload(decode=True))

        elif content_type == "text/html" and disposition not in ("attachment",):
            extractor = self.registry.get_extractor("html")
            if extractor is None:
                raise ValueError(
                    "HTML extractor not found in registry. Registry contains: "
                    + ", ".join(e.name for e in self.registry.extractors)
                )
            return extractor.extract_from_bytes(part.get_payload(decode=True))

        else:
            # Attachment or unsupported type — attempt extraction via registry,
            # always record the part even if no extractor exists so it can be
            # reprocessed when a suitable extractor becomes available.
            file_bytes = part.get_payload(decode=True)

            extractor = self.registry.get_extractor_for_content_type(content_type)

            if extractor is None:
                logger.debug(
                    f"No extractor for attachment '{filename}' ({content_type}); "
                    "recording as empty part."
                )
                return DocumentExtractionResult(
                    texts=[""],
                    content_types=[content_type],
                    metadata=[{"attachment_filename": filename, "content_type": content_type}],
                    unit_locators=[],
                    extractor_names=[""],
                    extractor_versions=[""],
                )

            if not file_bytes:
                logger.debug(f"Attachment '{filename}' has no payload.")
                return DocumentExtractionResult(
                    texts=[""],
                    content_types=[content_type],
                    metadata=[{
                        "attachment_filename": filename,
                        "content_type": content_type,
                        "extraction_error": "empty_payload",
                    }],
                    unit_locators=[],
                    extractor_names=[extractor.name],
                    extractor_versions=[extractor.version],
                )

            logger.debug(f"Extracting attachment '{filename}' ({content_type}) with '{extractor.name}'")
            try:
                result = extractor.extract_from_bytes(file_bytes)
                # Stamp attachment_filename onto every metadata entry returned
                for m in result.metadata:
                    m["attachment_filename"] = filename
                return result
            except Exception as e:
                logger.warning(f"Extractor '{extractor.name}' failed on '{filename}': {e}")
                return DocumentExtractionResult(
                    texts=[""],
                    content_types=[content_type],
                    metadata=[{
                        "attachment_filename": filename,
                        "content_type": content_type,
                        "extraction_error": str(e),
                    }],
                    unit_locators=[],
                    extractor_names=[extractor.name],
                    extractor_versions=[extractor.version],
                )

    def _extract_message(self, message: Message) -> DocumentExtractionResult:
        """
        Extract all parts of an email message into a single DocumentExtractionResult.
        Index 0 is the email body; each subsequent index is one MIME part/attachment.
        """
        shared_metadata = {
            "message_id": _safe_get_header(message, "Message-ID"),
            "subject": str(make_header(decode_header(message.get("Subject", "")))),
            "from": str(make_header(decode_header(message.get("From", "")))),
            "to": str(make_header(decode_header(message.get("To", "")))),
            "date": message.get("Date", ""),
            "cc": str(make_header(decode_header(message.get("Cc", "")))),
            "bcc": str(make_header(decode_header(message.get("Bcc", "")))),
        }

        if message.is_multipart():
            extraction_results = []
            unit_locators = []
            for part_id, part in enumerate(message.walk()):
                result = self._extract_part(part)
                if result is None:
                    continue
                unit_locators.append(f"message_part://{part_id}")
                extraction_results.append(result)
    
            if not extraction_results:
                logger.debug("No extractable parts found in multipart message; returning empty result.")
                return DocumentExtractionResult(
                    texts=[""],
                    content_types=[message.get_content_type()],
                    metadata=[shared_metadata],
                    unit_locators=["message_part://0"],
                    extractor_names=[self.name],
                    extractor_versions=[self.version],
                    is_multipart=False,
                )


            return DocumentExtractionResult(
                texts=[r.texts[0] for r in extraction_results],
                content_types=[r.content_types[0] for r in extraction_results],
                metadata=[{**shared_metadata, **r.metadata[0]} for r in extraction_results],
                unit_locators=unit_locators,
                extractor_names=[r.extractor_names[0] for r in extraction_results],
                extractor_versions=[r.extractor_versions[0] for r in extraction_results],
                is_multipart=True,
            )

        else:
            payload = message.get_payload(decode=True)
            text = payload.decode(
                message.get_content_charset() or "utf-8", errors="replace"
            ) if payload else ""
            return DocumentExtractionResult(
                texts=[text],
                content_types=[message.get_content_type()],
                metadata=[shared_metadata],
                unit_locators=["message_part://0"],
                extractor_names=[self.name],
                extractor_versions=[self.version],
            )

    def extract_from_bytes(self, file_bytes: bytes) -> DocumentExtractionResult:
        eml_str = file_bytes.decode("utf-8", errors="ignore")
        message = email.message_from_string(eml_str, policy=default)
        return self._extract_message(message)

    def extract(self, path: Path) -> DocumentExtractionResult:
        logger.debug(f"Extracting .eml file from path: {path}")
        eml_str = path.read_text(encoding="utf-8", errors="ignore")
        message = email.message_from_string(eml_str, policy=default)
        result = self._extract_message(message)
        # Stamp the filesystem locator onto the first part (email body)
        if result.unit_locators:
            result.unit_locators[0] = f"filesystem:{path.resolve()}"
        result.metadata[0]["filename"] = path.name
        result.metadata[0]["suffix"] = path.suffix
        return result


# Register the extractor
extractor_registry.register_extractor(EMLExtractor())
