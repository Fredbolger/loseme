import os
from pathlib import Path
from typing import List, Optional, Callable
from pydantic import PrivateAttr
import hashlib
from datetime import datetime
from src.domain.models import EmailDocument, ThunderbirdIndexingScope, IngestionSource
from src.domain.ids import make_logical_document_id, make_source_instance_id
from src.domain.extraction.registry import ExtractorRegistry
from fnmatch import fnmatch
from email.header import decode_header, make_header
import mailbox
import logging
import warnings

logger = logging.getLogger(__name__)

device_id = os.environ.get("LOSEME_DEVICE_ID")
if device_id is None:
    warnings.warn("LOSEME_DEVICE_ID environment variable is not set. Defaulting to 'unknown_device'.", UserWarning)
    device_id = "unknown_device"

import mailbox
from email.message import Message
from pathlib import Path


def extract_email_text(message: Message) -> str:
    parts = []
    if message.is_multipart():
        for part in message.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                try:
                    parts.append(part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="replace"
                    ))
                except:
                    pass
            elif ctype == "text/html":
                try:
                    html_content = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="replace"
                    )
                    parts.append(html_to_text_bs(html_content))
                except:
                    pass
    else:
        ctype = message.get_content_type()
        if ctype == "text/plain":
            try:
                parts.append(message.get_payload(decode=True).decode(
                    message.get_content_charset() or "utf-8", errors="replace"
                ))
            except:
                pass
        elif ctype == "text/html":
            try:
                html_content = message.get_payload(decode=True).decode(
                    message.get_content_charset() or "utf-8", errors="replace"
                )
                parts.append(html_to_text_bs(html_content))
            except:
                pass
    return "\n".join(parts)

class ThunderbirdIngestionSource(IngestionSource):
    """
    Ingestion source for Thunderbird mbox files.

    Args:
        scope (ThunderbirdIndexingScope): The indexing scope for Thunderbird.
        ignore_patterns (Optional[List[dict]]): List of ignore patterns to filter out emails.

    """ 
    _mbox_path: Path = PrivateAttr()
    _ignore_patterns: List[dict] = PrivateAttr()
    _metadata: dict = PrivateAttr()

    def __init__(self, 
                 scope: ThunderbirdIndexingScope, 
                 should_stop: Optional[Callable[[], bool]] = None
                 ):
        super().__init__(scope=scope, should_stop=should_stop)
        self.scope = scope
        self._mbox_path = scope.mbox_path
        self._ignore_patterns = scope.ignore_patterns or []
        self.should_stop = should_stop
        self._metadata = {
            "device_id": device_id,
            "source_instance_id": make_source_instance_id(
                source_type="thunderbird",
                source_path=Path(self._mbox_path),
                device_id=device_id
                ),
        }
    
    @property
    def mbox_path(self) -> Path:
        return self._mbox_path

    @property
    def ignore_patterns(self) -> List[dict]:
        return self._ignore_patterns
    @property
    def metadata(self) -> dict:
        return self._metadata

    def iter_documents(self) -> List[EmailDocument]:
        mbox = mailbox.mbox(self.mbox_path)

        for message in mbox:
            if self.should_stop():
                logger.info("Stop requested, terminating Thunderbird ingestion source.")
                break
            email_doc = self._build_email_document(
                message=message,
                mbox_path=str(self.mbox_path)
            )
            # Filter by metadata ignore patterns
            if self.ignore_patterns:
                skip = False
                for pattern in self.ignore_patterns:
                    field = pattern.get("field") # e.g. "From", "Subject"
                    value = pattern.get("value") # e.g. "*@spam.com"

                    if field and value:
                        field_value = email_doc.metadata.get(field)
                        if field_value and fnmatch(field_value.lower(), value):
                            logger.debug(
                                f"Excluding email with Message-ID {email_doc.message_id} "
                                f"due to ignore pattern on field '{field}' with value '{value}'."
                            )
                            skip = True
                            break
                if skip:
                    continue
            yield email_doc

    def _build_email_document(
        self,
        message: Message,
        mbox_path: str,
        ) -> EmailDocument:
        message_id = message.get("Message-ID")
        if not message_id:
            warnings.warn(f"Email message in {mbox_path} is missing Message-ID header. Using fallback ID.", UserWarning)
            message_id = self._fallback_message_id(message)
            

        text = extract_email_text(message)
        checksum = hashlib.sha256(
                    text.strip().encode("utf-8")
                    ).hexdigest()
        doc_id = make_logical_document_id(
                text=text,
        )

        return EmailDocument(
            id=doc_id,
            source_type="thunderbird",
            device_id=self.metadata["device_id"],
            mbox_path=mbox_path,
            message_id=message_id,
            text=text,
            checksum=checksum,
            metadata={
                **self.metadata,
                "subject": message.get("Subject"),
                "from": message.get("From"),
                "to": message.get("To"),
                "date": message.get("Date"),
            },
        )

    def _fallback_message_id(self, message: Message) -> str:
        # Fallback to a hash of From, To, Date, Subject if Message-ID is missing
        unique_string = f"{message.get('From')}|{message.get('To')}|{message.get('Date')}|{message.get('Subject')}"
        return hashlib.sha256(unique_string.encode("utf-8")).hexdigest()
