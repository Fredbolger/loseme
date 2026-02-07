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

"""
def extract_pdf_from_bytes(pdf_bytes: bytes) -> str:
    try:
        from src.sources.filesystem.pdf_extractor import PDFExtractor
        pdf_extractor = PDFExtractor()
        pdf_result = pdf_extractor.extract_from_bytes(pdf_bytes)
        return pdf_result.text
    except ImportError:
        logger.warning("PDF extraction requested but PDFExtractor is not available.")
        return ""
"""

def html_to_text_bs(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text("\n", strip=True)

class ThunderbirdExtractor(DocumentExtractor):
    name: str = "thunderbird"
    priority: int = 15

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

    def _extract_part_text(self, part) -> str:
        # This function extracts text from a single part of the email
        # It should only operate on non-multipart parts

        if part.is_multipart():
            logger.debug("Skipping multipart part in _extract_part_text")
            return ""

        if part.get_content_type() == "text/plain":
            return part.get_payload(decode=True).decode(
                part.get_content_charset() or "utf-8", errors="replace"
            )
        elif part.get_content_type() == "text/html":
            text = part.get_payload(decode=True).decode(
                part.get_content_charset() or "utf-8", errors="replace"
            )
            return html_to_text_bs(text)
        elif part.get_content_type() == "application/pdf":
            pdf_bytes = part.get_payload(decode=True)
            return self.extract_pdf_from_bytes(pdf_bytes)
        else:
            logger.debug(f"Skipping unsupported content type: {part.get_content_type()}")
            return ""

    def extract(self, path: Path):
        msg_id = "<" + path.name.strip("<>") + ">"
        mbox_folder = path.parent
        logger.debug(f"Extracting Thunderbird email from {mbox_folder}, message ID: {msg_id}")
        email_data = get_email_by_message_id(str(mbox_folder), msg_id)
        return email_data

    def extract_by_message_id(self, mbox_path: str, message_id: str) -> str:
        logger.debug(f"Extracting Thunderbird email from {mbox_path}, message ID: {message_id}")
        email_data = get_email_by_message_id(mbox_path, message_id)
        return email_data
    
    def extract_message_text(self, message: Message) -> str:
        text_body = ""

        if message.is_multipart():
            for part in message.walk():
                text_body += self._extract_part_text(part)
        else:
            payload = message.get_payload(decode=True)
            if payload:
                text_body += self._extract_part_text(message)
        return text_body 

    def extract_pdf_from_bytes(self, df_bytes: bytes) -> str:
        """
        Test if the registry, in which this extractor is registered, has a PDF extractor and use it to extract text from the PDF bytes
        """
            for extractor in self.registry.extractors:
        if extractor is self:
            continue
        if extractor.can_extract_bytes(df_bytes):
            result = extractor.extract_from_bytes(df_bytes)
            return result.text
        return ""

extractor_registry.register_extractor(ThunderbirdExtractor())
