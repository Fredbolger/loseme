from pydantic import BaseModel
from fastapi import HTTPException, APIRouter
from storage.metadata_db.document_parts import (upsert_document_part,
retrieve_scope_by_document_part_id, get_document_part_by_id,
get_all_document_parts_by_source_instance_id, get_document_stats,
                                                get_document_stats_per_source)
from storage.metadata_db.indexing_runs import increment_discovered_count
from src.sources.base.models import IngestionSource, Document, DocumentPart
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

class AddDiscoveredDocumentPartRequest(BaseModel):
    run_id: str
    document_part_id: str
    source_type: str
    checksum: str
    device_id: str
    source_path: str
    source_instance_id: str
    unit_locator: str 
    content_type: str
    extractor_name: str
    extractor_version: str
    metadata_json: Optional[dict] = {}
    created_at: str
    updated_at: str
    scope_json: Optional[dict] = None

class DocumentPartResponse(BaseModel):
    document_part_id: Optional[str] = None
    source_instance_id: Optional[str] = None
    part: dict

class BatchGetRequest(BaseModel):
    document_part_ids: list[str]

class DocumentStatResponse(BaseModel):
    total_document_parts: int
    total_sources: int
    total_devices: int

@router.post("/add_discovered_document_part")
def add_discovered_document_part_endpoint(req: AddDiscoveredDocumentPartRequest):
    """
    Mark a document as discovered but not yet indexed.

    Args:
        run_id: The ID of the indexing run.
        source_instance_id: The source instance ID of the document.
        content_checksum: The checksum of the document content.

    Returns:
        Success message.
    """
    upsert_document_part(
        part={
            "document_part_id": req.document_part_id,
            "checksum": req.checksum,
            "source_type": req.source_type,
            "source_instance_id": req.source_instance_id,
            "device_id": req.device_id,
            "source_path": req.source_path,
            "metadata_json": req.metadata_json,
            "unit_locator": req.unit_locator,
            "content_type": req.content_type,
            "extractor_name": req.extractor_name,
            "extractor_version": req.extractor_version,
            "created_at": req.created_at,
            "updated_at": req.updated_at,
            "scope_json": req.scope_json
        },
        run_id=req.run_id
    )

    increment_discovered_count(req.run_id)

    return {"status": "Document part marked as discovered."}


@router.get("/open/{document_part_id}")
def get_open_descriptor(document_part_id: str):
    doc_part = get_document_part_by_id(document_part_id)
    if doc_part is None:
        raise HTTPException(404, "Document not found")

    source_type, scope = retrieve_scope_by_document_part_id(document_part_id)
    source = IngestionSource.from_scope(scope, should_stop=lambda: False)

    return source.get_open_descriptor(doc_part)

@router.post("/batch_get")
def batch_get_document_parts(req: BatchGetRequest):
    """
    Retrieve multiple document parts by their IDs.

    Args:
        document_part_ids: List of document part IDs to retrieve.

    Returns:
        List of document metadata.
    """
    documents_parts = []
    for doc_part_id in req.document_part_ids:
        document_part = get_document_part_by_id(doc_part_id)
        if document_part:
            documents_parts.append(document_part)
    return {"documents_parts": documents_parts}


@router.get("/get_all_document_parts", response_model=list[DocumentPartResponse])
def get_all_document_parts_endpoint() -> list[DocumentPartResponse]:
    """
    Retrieve all document parts in the system.
    Returns:
        List of all document parts.
    """
    from storage.metadata_db.document_parts import get_all_document_part_ids

    document_part_ids = get_all_document_part_ids()
    document_parts = []
    for doc_part_id in document_part_ids:
        if doc_part_id is None:
            logger.warning(f"Document part with ID {doc_part_id} is None. Skipping.")
            continue
        document_part = get_document_part_by_id(doc_part_id)
        if document_part is None:
            logger.warning(f"Document part with ID {doc_part_id} not found. Skipping.")
            continue
        document_parts.append(DocumentPartResponse(document_part_id=doc_part_id, source_instance_id=document_part.get("source_instance_id"), part=document_part))

    return document_parts

@router.get("/stats", response_model=DocumentStatResponse)
def get_document_stats_endpoint() -> DocumentStatResponse:
    """
    Retrieve statistics about documents in the system.

    Returns:
        A dictionary containing document statistics.
    """
    
    stats = get_document_stats()
    logger.debug(f"Document stats retrieved: {stats}")
    return DocumentStatResponse(
        total_document_parts=stats.get("total_document_parts", 0),
        total_sources=stats.get("total_sources", 0),
        total_devices=stats.get("total_devices", 0)
    )


@router.get("/stats/per_source")
def get_document_stats_per_source_endpoint():
    """
    Retrieve statistics about documents grouped by source instance ID.

    Returns:
        A list of dictionaries containing document statistics per source instance ID.
    """
    from storage.metadata_db.document_parts import get_document_stats_per_source

    stats_per_source = get_document_stats_per_source()
    logger.debug(f"Document stats per source retrieved: {stats_per_source}")
    return {"stats_per_source": stats_per_source}

@router.get("/{document_part_id}")
def get_document_part(document_part_id: str):
    """
    Retrieve document metadata by document ID.

    Args:
        document_part_id: The ID of the document part to retrieve.

    Returns:
        Document metadata if found.

    Raises:
        HTTPException: If the document is not found.
    """
    document_part = get_document_part_by_id(document_part_id)
    
    if not document_part:
        logger.warning(f"Document part with ID {document_part_id} not found.")
        raise HTTPException(status_code=404, detail=f"Document with ID {document_part_id} not found.")
    
    return {"document_part": document_part}


@router.get("/preview/{document_part_id}")
def preview_document(document_part_id: str):
    logger.debug(f"Previewing document part with ID: {document_part_id}")
    doc_part = get_document_part_by_id(document_part_id)
    if doc_part is None:
        raise HTTPException(404, "Document not found")

    source_type, scope = retrieve_scope_by_document_part_id(document_part_id)

    if source_type == "thunderbird":
        # Parse source_path to get mbox path and message ID
        source_path_parts = doc_part["source_path"].split("::Message-ID:")
        mbox_path = source_path_parts[0]
        message_id = source_path_parts[1]

        from src.sources.base.docker_path_translation import host_path_to_container
        import mailbox, email as emaillib
        from email.header import decode_header, make_header

        container_mbox_path = host_path_to_container(mbox_path)
        logger.debug(f"Translated host mbox path '{mbox_path}' to container mbox path '{container_mbox_path}'")
        mbox = mailbox.mbox(str(container_mbox_path))
        mbox._generate_toc()

        target_message = None
        for msg in mbox:
            if msg.get("Message-ID") == message_id:
                target_message = msg
                break
        
        if target_message is None:
            raise HTTPException(404, "Email message not found in mbox")

        def decode_header_str(val):
            return str(make_header(decode_header(val or "")))

        # Extract raw HTML and plain text bodies directly
        body_html = None
        body_text = None
        if target_message.is_multipart():
            for part in target_message.walk():
                ct = part.get_content_type()
                if ct == "text/html" and body_html is None:
                    body_html = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="replace"
                    )
                elif ct == "text/plain" and body_text is None:
                    body_text = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="replace"
                    )
        else:
            payload = target_message.get_payload(decode=True)
            if payload:
                text = payload.decode(
                    target_message.get_content_charset() or "utf-8", errors="replace"
                )
                if target_message.get_content_type() == "text/html":
                    body_html = text
                else:
                    body_text = text

        return {
            "source_type": "thunderbird",
            "subject": decode_header_str(target_message.get("Subject")),
            "from":    decode_header_str(target_message.get("From")),
            "to":      decode_header_str(target_message.get("To")),
            "date":    target_message.get("Date", ""),
            "body_html": body_html,
            "body_text": body_text,
        }

    raise HTTPException(400, f"Preview not supported for source type: {source_type}")

"""
@router.get("/preview/{document_part_id}")
def preview_document(document_part_id: str):
    doc_part = get_document_part_by_id(document_part_id)
    if doc_part is None:
        raise HTTPException(404, "Document not found")

    source_type, scope = retrieve_scope_by_document_part_id(document_part_id)

    if source_type == "thunderbird":
        source = IngestionSource.from_scope(scope, should_stop=lambda: False)
        part = source.extract_by_document_part_id(document_part_id)

        if part is None:
            raise HTTPException(404, "Email message not found in mbox")

        metadata = part.metadata_json or {}
        return {
            "source_type": "thunderbird",
            "subject":    metadata.get("subject", ""),
            "from":       metadata.get("from", ""),
            "to":         metadata.get("to", ""),
            "date":       metadata.get("date", ""),
            "body_html":  part.text if part.content_type == "text/html" else None,
            "body_text":  part.text if part.content_type == "text/plain" else None,
        }

    raise HTTPException(400, f"Preview not supported for source type: {source_type}")
"""
