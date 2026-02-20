import os
from pathlib import Path
from typing import List, Optional, Callable
from pydantic import PrivateAttr
import hashlib
from datetime import datetime
from .thunderbird_model import ThunderbirdIndexingScope, ThunderbirdDocument
from src.sources.base.models import IngestionSource, OpenDescriptor, DocumentPart
from src.core.ids import make_logical_document_part_id, make_source_instance_id, make_thunderbird_source_id
from src.sources.base.registry import extractor_registry, ingestion_source_registry
from fnmatch import fnmatch
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime
import mailbox
import logging
import os
import json
import warnings

logger = logging.getLogger(__name__)

device_id = os.environ.get("LOSEME_DEVICE_ID", os.uname().nodename)

registry = extractor_registry

if device_id is None:
    raise ValueError("LOSEME_DEVICE_ID environment variable is not set.")
    
import mailbox
from email.message import Message
from pathlib import Path


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
                 should_stop: Optional[Callable[[], bool]] = None,
                 update_if_changed_after : Optional[datetime] = None
                 ):
        super().__init__(scope=scope, should_stop=should_stop)
        self.scope = scope
        self._mbox_path = scope.mbox_path
        self._ignore_patterns = scope.ignore_patterns or []
        self.should_stop = should_stop
        self.update_if_changed_after = update_if_changed_after
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

    def iter_documents(self) -> List[ThunderbirdDocument]:
        mbox = mailbox.mbox(self.mbox_path)
        logger.debug(f"Opened mbox file at {self.mbox_path} with {len(mbox)} messages.")

        for index in mbox.iterkeys():
            if self.should_stop():
                logger.info("Stop requested, terminating Thunderbird ingestion source.")
                break
            message_doc =  mbox.get(index)
        # Filter by metadata ignore patterns
            if self.ignore_patterns:
                skip = False
                for pattern in self.ignore_patterns:
                    field = pattern.get("field") # e.g. "From", "Subject"
                    value = pattern.get("value") # e.g. "*@spam.com"

                    if field and value:
                        field_value = message_doc.get(field)
                        if field_value and fnmatch(field_value.lower(), value):
                            logger.debug(
                                f"Excluding email with Message-ID {message_doc.get('Message-ID')} "
                                f"due to ignore pattern on field '{field}' with value '{value}'."
                            )
                            skip = True
                            break
                if skip:
                    continue
            logger.debug(f"Processing email with Message-ID {message_doc.get('Message-ID')} from mbox {self.mbox_path}.")
            email_doc = self._build_email_document(message=message_doc,
                                                   mbox_path=str(self.mbox_path))
            
            yield email_doc

    def _build_email_document(
        self,
        message: Message,
        mbox_path: str,
        ) -> ThunderbirdDocument:
        message_id = message.get("Message-ID")
        if not message_id:
            warnings.warn(f"Email message in {mbox_path} is missing Message-ID header. Using fallback ID.", UserWarning)
            message_id = self._fallback_message_id(message)
            
        doc_id = make_thunderbird_source_id(
                device_id=device_id,
                mbox_path=mbox_path,
                message_id=message_id
                )
        source_instance_id = make_source_instance_id(
                source_type="thunderbird",
                source_path=Path(mbox_path) / f"Message-ID:{message_id}",
                device_id=device_id
                )
    
        received_date = self.extract_datetime(message)
        extraction_result = registry.get_extractor("thunderbird").extract_message_text(message)
        texts = extraction_result.texts
        merged_text = "\n".join(texts)
        checksum = hashlib.sha256(
                    merged_text.strip().encode("utf-8")
                    ).hexdigest() 
        
        thunderbird_document = ThunderbirdDocument(
            id=doc_id,
            source_type="thunderbird",
            device_id=self.metadata["device_id"],
            mbox_path=mbox_path,
            message_id=message_id,
            checksum=checksum,
            metadata={
                **self.metadata,
                "subject": message.get("Subject"),
                "from": message.get("From"),
                "to": message.get("To"),
                "date": message.get("Date"),
            },
        )
        for part_id, part_text in enumerate(extraction_result.texts):
            part = DocumentPart(
                document_part_id=make_logical_document_part_id(
                    source_instance_id=source_instance_id,
                    unit_locator=extraction_result.unit_locators[part_id],
                ),
                text=part_text,
                checksum=checksum,
                device_id=device_id,
                source_path=f"{mbox_path}::Message-ID:{message_id}",
                source_type="thunderbird",
                source_instance_id=source_instance_id,
                unit_locator=extraction_result.unit_locators[part_id],
                content_type=extraction_result.content_types[part_id],
                extractor_name=extraction_result.extractor_names[part_id],
                extractor_version=extraction_result.extractor_versions[part_id],
                metadata_json=extraction_result.metadata[part_id],
                created_at=received_date or datetime.utcnow(),
                updated_at=received_date or datetime.utcnow(),
                )

            thunderbird_document.add_part(part)

        # If the metadata contains non-JSON-serializable values, convert them to strings
        for k, v in thunderbird_document.metadata.items():
            try:
                json.dumps(v)
            except TypeError:
                thunderbird_document.metadata[k] = str(v)
        return thunderbird_document

    def _fallback_message_id(self, message: Message) -> str:
        # Fallback to a hash of From, To, Date, Subject if Message-ID is missing
        unique_string = f"{message.get('From')}|{message.get('To')}|{message.get('Date')}|{message.get('Subject')}"
        return hashlib.sha256(unique_string.encode("utf-8")).hexdigest()

    def get_open_descriptor(self, email_document: dict) -> OpenDescriptor:
        return OpenDescriptor(
            source_type="thunderbird",
            target=email_document["source_path"],
        )

    def extract_by_document_id(self,
                             document_id: str
                               ) -> Optional[ThunderbirdDocument]:
        """
        Extract a single email document's content by its document ID.
        """

        doc_record = get_document_by_id(document_id)

        if doc_record is None:
            raise ValueError(f"Document with ID {document_id} not found in metadata database.")
            return None

        logger.debug(f"Retrieved document record for ID {document_id}: {doc_record}")

        mbox_path = self.mbox_path
        mbox = mailbox.mbox(mbox_path)
        
        logger.debug(f"Searching for document ID {document_id} in mbox {mbox_path}.")
    
        for message in mbox:
            email_doc = self._build_email_document(
                message=message,
                mbox_path=str(mbox_path)
            )
            if email_doc.id == document_id:
                return email_doc

        raise ValueError(f"Document with ID {document_id} not found in mbox {mbox_path}.")
        return None
    
    def extract_by_document_ids(self,
                                 document_ids: List[str]
                                   ) -> List[ThunderbirdDocument]:
        """
        Extract multiple email documents' content by their document IDs.
        """

        doc_records = [get_document_by_id(doc_id) for doc_id in document_ids]
        found_doc_ids = {doc['document_id'] for doc in doc_records if doc is not None}

        logger.debug(f"Retrieved document records for IDs {document_ids}: {doc_records}")

        mbox_path = self.mbox_path
        mbox = mailbox.mbox(mbox_path)
        
        logger.debug(f"Searching for document IDs {document_ids} in mbox {mbox_path}.")

        extracted_documents = []

        for message in mbox:
            email_doc = self._build_email_document(
                message=message,
                mbox_path=str(mbox_path)
            )
            if email_doc.id in found_doc_ids:
                extracted_documents.append(email_doc)
                if len(extracted_documents) == len(found_doc_ids):
                    break

        if len(extracted_documents) < len(found_doc_ids):
            missing_ids = found_doc_ids - {doc.id for doc in extracted_documents}
            logger.warning(f"Documents with IDs {missing_ids} not found in mbox {mbox_path}.")

        return extracted_documents

    def extract_datetime(self, message: Message) -> Optional[datetime]:
        received_headers = message.get_all("Received", [])
        for header in received_headers:
            if ";" in header:
                date_str = header.split(";")[-1].strip()
                try:
                    return parsedate_to_datetime(date_str)
                except (TypeError, ValueError):
                    continue

        

ingestion_source_registry.register_source("thunderbird", ThunderbirdIngestionSource)
