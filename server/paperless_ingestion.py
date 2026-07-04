"""
Paperless-ngx ingestion source implementation for Loseme server.

This module provides the actual implementation of PaperlessIngestionSource
that can be used by the server to ingest documents from Paperless-ngx instances.
"""

import os
import json
from typing import List, Optional, Callable, Dict, Any
from datetime import datetime, timezone
import hashlib
import logging
from pydantic import ConfigDict

from loseme_core.models import IngestionSource, OpenDescriptor, Document, DocumentPart
from loseme_core.paperless_model import PaperlessIndexingScope, PaperlessDocument
from loseme_core.ids import make_paperless_source_id, make_logical_document_part_id
from storage.metadata_db.paperless_connections import get_paperless_connection, get_connection_url_and_token
from paperless_api_client import PaperlessApiClient

logger = logging.getLogger(__name__)

# Get device ID from environment
device_id = os.environ.get("LOSEME_DEVICE_ID", "server")


class PaperlessIngestionSource(IngestionSource):
    """
    Ingestion source for Paperless-ngx documents.
    
    This implementation handles the actual ingestion of documents from Paperless-ngx instances.
    It uses the Paperless API client to fetch documents and their content.
    """
    
    # Pydantic model config to allow extra fields
    model_config = ConfigDict(extra="allow")
    
    # Private fields that won't be validated as Pydantic fields
    __pydantic_private__ = {"connection", "api_client"}
    
    def __init__(self, 
                 scope: PaperlessIndexingScope,
                 should_stop: Optional[Callable[[], bool]] = None,
                 update_if_changed_after: Optional[datetime] = None
                 ):
        super().__init__(scope=scope, should_stop=should_stop, update_if_changed_after=update_if_changed_after)
        self.scope = scope
        self.should_stop = should_stop or (lambda: False)
        self.update_if_changed_after = update_if_changed_after

        # Get the connection details
        connection = get_paperless_connection(scope.connection_id)
        if connection is None:
            raise ValueError(f"Paperless connection with ID {scope.connection_id} not found")
        
        # Initialize the API client
        api_client = PaperlessApiClient(
            base_url=connection.base_url,
            api_token=connection.api_token
        )
        
        # Store as instance attributes
        self.connection = connection
        self.api_client = api_client
        
        logger.info(f"Initialized PaperlessIngestionSource for connection {scope.connection_id}")
        logger.debug(f"Filters: tags={scope.tag_ids}, correspondents={scope.correspondent_ids}, document_types={scope.document_type_ids}")

    def _get_documents_to_ingest(self) -> List[Dict[str, Any]]:
        """
        Get all documents from Paperless that match the scope filters.
        
        Returns:
            List of document metadata dictionaries
        """
        try:
            logger.debug(f"Fetching documents from Paperless with filters: tag_ids={self.scope.tag_ids}, correspondent_ids={self.scope.correspondent_ids}, document_type_ids={self.scope.document_type_ids}")
            
            documents = self.api_client.list_all_documents(
                tag_ids=self.scope.tag_ids,
                correspondent_ids=self.scope.correspondent_ids,
                document_type_ids=self.scope.document_type_ids
            )
            
            logger.info(f"Found {len(documents)} documents matching Paperless filters")
            logger.debug(f"First few documents: {documents[:3] if documents else 'No documents'}")
            logger.debug(f"Types of documents: {[type(d) for d in documents[:5]] if documents else 'No documents'}")
            
            # Validate that all items are dictionaries with expected fields
            validated_docs = []
            for i, doc in enumerate(documents):
                if not isinstance(doc, dict):
                    logger.error(f"Document at index {i} is not a dict, it's a {type(doc)}: {doc}")
                    continue
                if "id" not in doc:
                    logger.error(f"Document at index {i} is missing 'id' field: {doc}")
                    continue
                validated_docs.append(doc)
            
            if len(validated_docs) < len(documents):
                logger.warning(f"Filtered out {len(documents) - len(validated_docs)} invalid documents")
            
            return validated_docs
            
        except Exception as e:
            logger.error(f"Error fetching documents from Paperless: {str(e)}")
            raise

    def _create_document_part(self, paperless_doc: Dict[str, Any]) -> DocumentPart:
        """
        Create a DocumentPart from a Paperless document.
        
        Args:
            paperless_doc: Paperless document metadata
            
        Returns:
            DocumentPart object ready for ingestion
        """
        # Safeguard: ensure paperless_doc is a dict
        if not isinstance(paperless_doc, dict):
            logger.error(f"_create_document_part received non-dict: {paperless_doc} (type: {type(paperless_doc)})")
            raise ValueError(f"Expected dict, got {type(paperless_doc)}: {paperless_doc}")
        
        paperless_doc_id = str(paperless_doc.get("id"))
        
        # Create source ID using device_id and paperless document ID
        source_id = make_paperless_source_id(
            device_id=device_id,
            paperless_document_id=paperless_doc_id
        )
        
        # Create source instance ID (same as source_id for Paperless)
        source_instance_id = source_id
        
        # Use the paperless document ID as the unit locator
        unit_locator = paperless_doc_id
        
        # Create source path using Paperless title and ID
        title = paperless_doc.get("title", "Unknown")
        source_path = f"paperless:{paperless_doc_id}:{title}"
        
        # Get the modified timestamp for fingerprinting
        modified_timestamp = paperless_doc.get("modified", "")
        
        # Create a stable checksum based on the document content
        # We use the modified timestamp + document ID as a fingerprint for change detection
        fingerprint_text = f"{paperless_doc_id}:{modified_timestamp}"
        checksum = hashlib.sha256(fingerprint_text.encode()).hexdigest()
        
        # Get document content (OCR text)
        # First try to get content from the document object itself (Paperless may include it in the response)
        text_content = paperless_doc.get("content", "") or ""
        
        # Log content source for debugging
        if text_content and text_content.strip():
            logger.debug(f"Document {paperless_doc_id}: Using content from document object ({len(text_content)} chars)")
        else:
            logger.debug(f"Document {paperless_doc_id}: Content field empty or missing, fetching full document from API")
            # Fetch the full document which should include content
            try:
                full_doc = self.api_client.get_document(int(paperless_doc_id))
                text_content = full_doc.get("content", "") or ""
                if text_content and text_content.strip():
                    logger.debug(f"Document {paperless_doc_id}: Successfully got content from full document ({len(text_content)} chars)")
                else:
                    # Try the content endpoint as fallback
                    logger.debug(f"Document {paperless_doc_id}: Full document has no content, trying content endpoint")
                    try:
                        text_content = self.api_client.get_document_full_text(int(paperless_doc_id))
                        if text_content and text_content.strip():
                            logger.debug(f"Document {paperless_doc_id}: Successfully fetched content from content endpoint ({len(text_content)} chars)")
                    except Exception as e:
                        logger.warning(f"Could not extract text from Paperless document {paperless_doc_id}: {str(e)}")
                        text_content = ""
            except Exception as e:
                logger.warning(f"Could not fetch full document for {paperless_doc_id}: {str(e)}")
                text_content = ""
        
        # Extract metadata
        metadata = self._extract_metadata(paperless_doc)
        
        # Log final text length
        logger.debug(f"Document {paperless_doc_id}: Final text content length: {len(text_content)} chars")
        
        # Create scope JSON
        scope_json = self.scope.serialize()
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Create the DocumentPart
        part = DocumentPart(
            document_part_id=make_logical_document_part_id(source_instance_id, unit_locator),
            checksum=checksum,
            source_type="paperless",
            source_instance_id=source_instance_id,
            device_id=device_id,
            source_path=source_path,
            unit_locator=unit_locator,
            content_type=paperless_doc.get("mime_type", "application/octet-stream"),
            extractor_name="paperless_ngx",
            extractor_version="1.0",
            metadata_json=metadata,
            created_at=paperless_doc.get("created", now),
            updated_at=paperless_doc.get("modified", now),
            text=text_content,
            scope_json=scope_json,
        )
        
        return part

    def _extract_metadata(self, paperless_doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from a Paperless document.
        
        Args:
            paperless_doc: Paperless document metadata
            
        Returns:
            Dictionary with metadata for the document
        """
        def get_name_or_id(field_value: Any, field_name: str) -> tuple:
            """Helper to extract name and id from a field that might be an int or a dict."""
            if field_value is None:
                return None, None
            if isinstance(field_value, dict):
                return field_value.get("name"), field_value.get("id")
            elif isinstance(field_value, int):
                # Field is just an ID, no name available
                return None, field_value
            else:
                # Unexpected type, return as-is
                return field_value, None
        
        correspondent_name, correspondent_id = get_name_or_id(paperless_doc.get("correspondent"), "correspondent")
        document_type_name, document_type_id = get_name_or_id(paperless_doc.get("document_type"), "document_type")
        
        return {
            "paperless_document_id": str(paperless_doc.get("id")),
            "title": paperless_doc.get("title", ""),
            "original_filename": paperless_doc.get("original_file_name", ""),
            "created": paperless_doc.get("created"),
            "modified": paperless_doc.get("modified"),
            "added": paperless_doc.get("added"),
            "mime_type": paperless_doc.get("mime_type", "application/octet-stream"),
            "page_count": paperless_doc.get("page_count", 1),
            "file_size": paperless_doc.get("file_size"),
            "checksum": paperless_doc.get("checksum"),
            "storage_path": paperless_doc.get("storage_path"),
            
            # Tags - these should always be lists of dicts
            "tags": [tag.get("name") for tag in paperless_doc.get("tags", []) if isinstance(tag, dict)],
            "tag_ids": [tag.get("id") for tag in paperless_doc.get("tags", []) if isinstance(tag, dict)],
            
            # Correspondent - can be int, dict, or None
            "correspondent": correspondent_name,
            "correspondent_id": correspondent_id,
            
            # Document type - can be int, dict, or None  
            "document_type": document_type_name,
            "document_type_id": document_type_id,
        }

    def iter_documents(self) -> List[Document]:
        """
        Yield documents for ingestion from Paperless.
        
        Returns:
            List of Document objects ready for ingestion
        """
        documents = []
        
        try:
            # Get all documents matching our filters
            paperless_docs = self._get_documents_to_ingest()
            
            # Check if we should stop before processing
            if self.should_stop():
                logger.info("Paperless ingestion stopped by request")
                return documents
            
            for paperless_doc in paperless_docs:
                # Validate document structure
                logger.debug(f"Processing document: {paperless_doc} (type: {type(paperless_doc)})")
                if not isinstance(paperless_doc, dict):
                    logger.error(f"Skipping non-dict document: {paperless_doc} (type: {type(paperless_doc)})")
                    continue
                
                if "id" not in paperless_doc:
                    logger.error(f"Skipping document missing 'id' field: {paperless_doc}")
                    continue
                
                # Check if we should stop after each document
                if self.should_stop():
                    logger.info("Paperless ingestion stopped by request after processing some documents")
                    break
                
                # Check if document has been modified since last update
                if self.update_if_changed_after:
                    modified_str = paperless_doc.get("modified", "")
                    if modified_str:
                        try:
                            modified_time = datetime.fromisoformat(modified_str.replace("Z", "+00:00"))
                            if modified_time <= self.update_if_changed_after:
                                logger.debug(f"Skipping Paperless document {paperless_doc.get('id')} - not modified since {self.update_if_changed_after}")
                                continue
                        except ValueError:
                            logger.warning(f"Could not parse modified timestamp for document {paperless_doc.get('id')}: {modified_str}")
                
                # Create document part
                try:
                    part = self._create_document_part(paperless_doc)
                    
                    # Create a Document containing this part
                    document = Document(
                        id=part.document_part_id,
                        source_type="paperless",
                        source_id=part.source_instance_id,
                        device_id=part.device_id,
                        source_path=part.source_path,
                        metadata=part.metadata_json,
                        checksum=part.checksum,
                        created_at=part.created_at,
                        updated_at=part.updated_at,
                        parts=[part],
                    )
                    
                    documents.append(document)
                    logger.debug(f"Created document for Paperless document ID {paperless_doc.get('id')}")
                    
                except Exception as e:
                    logger.error(f"Error creating document from Paperless document {paperless_doc.get('id')}: {str(e)}")
                    continue
            
            logger.info(f"Paperless ingestion: Processed {len(documents)} documents")
            
        except Exception as e:
            logger.error(f"Error in Paperless ingestion: {str(e)}")
            raise
        
        return documents

    def get_open_descriptor(self, document_part_id: str) -> OpenDescriptor:
        """
        Describe how this document should be opened by a client.
        
        For Paperless documents, this will use the proxy endpoint to avoid
        exposing credentials to the client.
        
        Args:
            document_part_id: The document part ID
            
        Returns:
            OpenDescriptor for the document
        """
        # Parse the document_part_id to extract the Paperless document ID
        # The document_part_id is a hash, but we can get the source from the database
        doc_part = None
        try:
            from storage.metadata_db.document_parts import get_document_part_by_id
            doc_part = get_document_part_by_id(document_part_id)
        except ImportError:
            logger.error("Could not import get_document_part_by_id")
            # Fallback: create a URL-based descriptor
            return OpenDescriptor(
                source_type="paperless_proxy",
                target=f"/api/paperless/proxy/{document_part_id}",
                extra={"connection_id": self.scope.connection_id}
            )
        
        if doc_part:
            # Try to extract Paperless document ID from metadata
            metadata = doc_part.get("metadata_json", {})
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}
            
            paperless_doc_id = metadata.get("paperless_document_id")
            if paperless_doc_id:
                return OpenDescriptor(
                    source_type="paperless_proxy",
                    target=f"/api/paperless/proxy/{paperless_doc_id}",
                    extra={"connection_id": self.scope.connection_id, "document_part_id": document_part_id}
                )
        
        # Fallback descriptor
        return OpenDescriptor(
            source_type="paperless_proxy",
            target=f"/api/paperless/proxy/{document_part_id}",
            extra={"connection_id": self.scope.connection_id}
        )

    def extract_by_document_id(self, document_part_id: str) -> Optional[Document]:
        """
        Extract the full Document by its ID.
        
        This is used for re-extraction of individual documents.
        
        Args:
            document_part_id: The document part ID
            
        Returns:
            Document object or None if not found
        """
        try:
            # Get the document part from database to get metadata
            from storage.metadata_db.document_parts import get_document_part_by_id
            doc_part = get_document_part_by_id(document_part_id)
            
            if doc_part is None:
                logger.warning(f"Document part with ID {document_part_id} not found")
                return None
            
            # Try to extract Paperless document ID from metadata
            metadata = doc_part.get("metadata_json", {})
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}
            
            paperless_doc_id = metadata.get("paperless_document_id")
            if paperless_doc_id is None:
                logger.error(f"Could not find paperless_document_id in metadata for {document_part_id}")
                return None
            
            # Get the full document from Paperless
            try:
                paperless_doc = self.api_client.get_document(int(paperless_doc_id))
                part = self._create_document_part(paperless_doc)
                
                document = Document(
                    id=part.document_part_id,
                    source_type="paperless",
                    source_id=part.source_instance_id,
                    device_id=part.device_id,
                    source_path=part.source_path,
                    metadata=part.metadata_json,
                    checksum=part.checksum,
                    created_at=part.created_at,
                    updated_at=part.updated_at,
                    parts=[part],
                )
                
                return document
                
            except Exception as e:
                logger.error(f"Error extracting Paperless document {paperless_doc_id}: {str(e)}")
                return None
                
        except Exception as e:
            logger.error(f"Error in extract_by_document_id for {document_part_id}: {str(e)}")
            return None