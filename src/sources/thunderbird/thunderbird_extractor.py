from pathlib import Path
from src.sources.base.extractor import DocumentExtractor, DocumentExtractionResult
from src.sources.base.registry import extractor_registry
from email.header import decode_header, make_header
import mailbox
from email.message import Message
from bs4 import BeautifulSoup

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def is_mbox_file(path: str) -> bool:
    try:
        mbox = mailbox.mbox(path)
        # Force iteration to trigger parsing
        for _ in mbox:
            return True
        return False
    except Exception:
        return False

class ThunderbirdExtractor(DocumentExtractor):
    name: str = "thunderbird"
    priority: int = 15
    supported_mime_types: set[str] = {"message/rfc822"} # This refers to the email message format, not the attachments
    version: str = "0.1"

    def can_extract(self, path: Path) -> bool:
        try:
            msg_id = path.name.strip("<>")
            mbox_folder = path.parent
        except Exception:
            return False
        return is_mbox_file(str(mbox_folder))
    
    def can_extract_bytes(self, file_bytes: bytes) -> bool:
        # We won't implement byte extraction for Thunderbird emails
        return False

    def _extract_part(self, part) -> DocumentExtractionResult:
        # This function extracts a single part of the email
        # It should only operate on non-multipart parts

        if part.is_multipart():
            logger.debug("Skipping multipart part in _extract_part_text")
            return False
    
        # also skip encrypted parts 
        elif part.get_content_type() == "application/pkcs7-mime":
            logger.debug("Skipping encrypted part in _extract_part_text")
            return False

        if part.get_content_type() == "text/plain":
            # Use the extractor from the registry to extract text from the plain text part
            plain_text_extractor = self.registry.get_extractor("plaintext")
            if plain_text_extractor is None:
                raise ValueError("Plain text extractor not found in registry") 

            plain_text_extraction = plain_text_extractor.extract_from_bytes(part.get_payload(decode=True))
            return plain_text_extraction
        
        elif part.get_content_type() == "text/html":
            html_extractor = self.registry.get_extractor("html")
            if html_extractor is None:
                raise ValueError("HTML extractor not found in registry. Registry contains the following extractors: " + ", ".join([extractor.name for extractor in self.registry.extractors]))
            html_text_extraction = html_extractor.extract_from_bytes(part.get_payload(decode=True))
            return html_text_extraction
        
        elif part.get_content_type() == "application/pdf":
            pdf_extractor = self.registry.get_extractor("pdf")
            if pdf_extractor is None:
                raise ValueError("PDF extractor not found in registry")
            pdf_extraction = pdf_extractor.extract_from_bytes(part.get_payload(decode=True))
            return pdf_extraction
        
        else:
            logger.debug(f"Skipping unsupported content type: {part.get_content_type()}")
            return DocumentExtractionResult(
                texts=[""],
                content_types=[part.get_content_type()],
                metadata=[{}],
                unit_locators=[],
                extractor_names=["unsupported"],
                extractor_versions=["None"],
            )
    
    def extract(self, path: Path) -> DocumentExtractionResult:
        msg_id = "<" + path.name.strip("<>") + ">"
        mbox_folder = path.parent
        logger.debug(f"Extracting Thunderbird email from {mbox_folder}, message ID: {msg_id}")
        email_data = get_email_by_message_id(str(mbox_folder), msg_id)
        return email_data

    def extract_message_text(self, message: Message) -> DocumentExtractionResult:
        if message.is_multipart():
            extraction_results = []
            unit_locators = []
            for part_id, part in enumerate(message.walk()):
                extraction_result = self._extract_part(part)
                if not extraction_result:
                    continue
                unit_locators.append(f"message_part://{part_id}")
                extraction_results.append(extraction_result)
            
            return DocumentExtractionResult(
                texts=[result.texts[0] for result in extraction_results],
                content_types=[result.content_types[0] for result in extraction_results],
                metadata=[{
                    "message_id": message.get("Message-ID"),
                    "subject": str(make_header(decode_header(message.get("Subject", "")))),
                    "from": str(make_header(decode_header(message.get("From", "")))),
                    "to": str(make_header(decode_header(message.get("To", "")))),
                    "date": message.get("Date"),
                }] * len(extraction_results),
                unit_locators=unit_locators,
                extractor_names= [result.extractor_names[0] for result in extraction_results],
                extractor_versions=[result.extractor_versions[0] for result in extraction_results],
            )

        else:
            payload = message.get_payload(decode=True)
            if payload:
                texts = [payload.decode(message.get_content_charset() or "utf-8", errors="replace")]
                content_types = [message.get_content_type()]
        
            return DocumentExtractionResult(texts=texts, 
                                            content_types=content_types, 
                                            metadata=[{
                        "message_id": message.get("Message-ID"),
                        "subject": str(make_header(decode_header(message.get("Subject", "")))),
                        "from": str(make_header(decode_header(message.get("From", "")))),
                        "to": str(make_header(decode_header(message.get("To", "")))),
                        "date": message.get("Date"),
                    }],
                                            unit_locators=[f"message_part://0"],
                                            extractor_names=[self.name], 
                                            extractor_versions=[self.version]
                                            )

    def extract_pdf_from_bytes(self, df_bytes: bytes) -> str:
        """
        Test if the registry, in which this extractor is registered, has a PDF extractor and use it to extract text from the PDF bytes
        """
        for extractor in self.registry.extractors:
            if extractor is self:
                continue
            if extractor.can_extract_bytes(df_bytes):
                if extractor == None:
                    raise ValueError("PDF extractor not found in registry")
                result = extractor.extract_from_bytes(df_bytes)
                return result.texts[0] if result.texts else ""
            return ""

extractor_registry.register_extractor(ThunderbirdExtractor())
