import os
from pathlib import Path
from typing import List, Optional
import hashlib
from datetime import datetime
from src.domain.models import EmailDocument, IndexingScope
from src.domain.ids import make_logical_document_id, make_source_instance_id
from src.domain.extraction.registry import ExtractorRegistry
from fnmatch import fnmatch
from email.header import decode_header, make_header
import mailbox
import logging
import warnings

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

device_id = os.environ.get("LOSEME_DEVICE_ID")
if device_id is None:
    warnings.warn("LOSEME_DEVICE_ID environment variable is not set. Defaulting to 'unknown_device'.", UserWarning)
    device_id = "unknown_device"

LOSEME_DATA_DIR = Path(os.environ.get("LOSEME_DATA_DIR"))
if LOSEME_DATA_DIR is None:
    warnings.warn("LOSEME_DATA_DIR environment variable is not set. Defaulting to '/data'.", UserWarning)

LOSEME_SOURCE_ROOT_HOST = Path(os.environ.get("LOSEME_SOURCE_ROOT_HOST"))
if LOSEME_SOURCE_ROOT_HOST is None:
    warnings.warn("LOSEME_SOURCE_ROOT_HOST environment variable is not set. Defaulting to '/host_data'.", UserWarning)


class ThunderbirdIngestionSource:
    def __init__(self, 
                 scope: IndexingScope,
                 extractor_registry: ExtractorRegistry
                 ):
        self.scope = scope
        self.extractor_registry = extractor_registry

    def list_emails(self, mbox_path: Path) -> List[EmailDocument]:
        mbox = mailbox.mbox(mbox_path)
        emails = []

        for message in mbox:
            subject = str(make_header(decode_header(message.get('subject', "No Subject"))))
            sender = message.get('from', "Unknown Sender")
            date = message.get('date')
            try:
                date_parsed = datetime.strptime(date, '%a, %d %b %Y %H:%M:%S %z') if date else None
            except ValueError:
                date_parsed = None

            # Extract plain text body
            text = ""
            if message.is_multipart():
                parts = []
                for part in message.walk():
                    ctype = part.get_content_type()
                    disp = str(part.get("Content-Disposition") or "")
                    if ctype == "text/plain" and "attachment" not in disp:
                        try:
                            part_payload = part.get_payload(decode=True).decode(
                                part.get_content_charset() or "utf-8", errors="ignore"
                            )
                            parts.append(part_payload)
                        except:
                            pass
                text = "\n".join(parts)
            else:
                try:
                    text = message.get_payload(decode=True).decode(
                        message.get_content_charset() or "utf-8", errors="ignore"
                    )
                except:
                    text = ""

            logical_document_id = make_logical_document_id(text)
            email_checksum = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

            email_doc = EmailDocument(
                id=logical_document_id,
                mbox_id=str(message.get('message-id')),
                mbox_path=str(mbox_path),
                checksum=email_checksum,
                metadata={
                    "subject": subject,
                    "from": sender,
                    "date": date_parsed.isoformat() if date_parsed else None,
                }
            )
            emails.append(email_doc)
        return emails 
