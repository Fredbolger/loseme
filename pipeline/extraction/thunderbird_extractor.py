from pathlib import Path
from pipeline.extraction.base import DocumentExtractor, DocumentExtractionResult
from email.header import decode_header, make_header
import mailbox
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


def html_to_text_bs(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text("\n", strip=True)

def get_email_by_message_id(mbox_path: str, msg_id: str) -> str:
    """
    Retrieve an email from an mbox by its Message-ID header.
    Returns a clean plain-text representation.
    """
    mbox = mailbox.mbox(mbox_path)

    for message in mbox:
        if str(message.get("message-id", "")).strip() != msg_id.strip():
            continue

        # Decode headers
        subject = str(make_header(decode_header(message.get("subject", "No Subject"))))
        sender = message.get("from", "Unknown Sender")
        receiver = message.get("to", "Unknown Receiver")
        date = message.get("date", "Unknown Date")

        text_body = ""
        html_body = ""

        if message.is_multipart():
            for part in message.walk():
                ctype = part.get_content_type()
                if ctype == "text/plain":
                    try:
                        text_body += part.get_payload(decode=True).decode(
                            part.get_content_charset() or "utf-8", errors="replace"
                        )
                    except:
                        pass
                elif ctype == "text/html":
                    try:
                        html_body += part.get_payload(decode=True).decode(
                            part.get_content_charset() or "utf-8", errors="replace"
                        )
                    except:
                        pass
        else:
            payload = message.get_payload(decode=True)
            if payload:
                decoded = payload.decode(
                    message.get_content_charset() or "utf-8", errors="replace"
                )
                if message.get_content_type() == "text/plain":
                    text_body = decoded
                elif message.get_content_type() == "text/html":
                    html_body = decoded

        # Prefer plain text, fallback to HTML
        body = text_body.strip() or html_to_text_bs(html_body)

        return (
            f"From: {sender}\n"
            f"To: {receiver}\n"
            f"Subject: {subject}\n"
            f"Date: {date}\n\n"
            f"{body}"
        )

    raise ValueError(f"Message ID {msg_id} not found in {mbox_path}")

class ThunderbirdExtractor(DocumentExtractor):
    priority: int = 15

    def can_extract(self, path: Path) -> bool:
        try:
            msg_id = path.name.strip("<>")
            mbox_folder = path.parent
        except Exception:
            return False
        return is_mbox_file(str(mbox_folder))

    def extract(self, path: Path):
        msg_id = "<" + path.name.strip("<>") + ">"
        mbox_folder = path.parent
        logger.debug(f"Extracting Thunderbird email from {mbox_folder}, message ID: {msg_id}")
        email_data = get_email_by_message_id(str(mbox_folder), msg_id)
        return email_data
