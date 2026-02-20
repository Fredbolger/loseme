from pydantic import BaseModel
from fastapi import HTTPException, APIRouter
from storage.metadata_db.document_parts import upsert_document_part, retrieve_scope_by_document_part_id, get_document_part_by_id, get_all_document_parts_by_source_instance_id
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

'''
@router.get("/get_all_documents", response_model=AllDocumentsResponse)
def get_all_documents_endpoint() -> AllDocumentsResponse:
    """
    Retrieve all documents in the system.
    Returns:
        List of all documents.
    """

    recieved_documents = get_all_document_ids()
    document_ids = [doc["document_id"] for doc in recieved_documents]
    source_ids = [doc["source_instance_id"] for doc in recieved_documents]
    documents = []
    for doc_id, source_id in zip(document_ids, source_ids):
        if doc_id is None:
            logger.warning(f"Document with source_id {source_id} has no document_id. Skipping.")
            continue
        if source_id is None:
            logger.warning(f"Document with ID {doc_id} has no source_id. Skipping.")
            continue
        parts = get_all_parts(doc_id)
        documents.append(DocumentPartsResponse(document_id=doc_id, source_instance_id=source_id, parts=parts))

    return AllDocumentsResponse(documents=documents)
'''

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
    
    if not document:
        raise HTTPException(status_code=404, detail=f"Document with ID {document_id} not found.")
    
    return {"document_part": document_part}

