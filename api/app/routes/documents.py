from pydantic import BaseModel
from fastapi import HTTPException, APIRouter
from storage.metadata_db.document import get_document_by_id as get_document_from_db
from storage.metadata_db.document import retrieve_source
from storage.metadata_db.processed_documents import add_discovered_document
from storage.metadata_db.indexing_runs import increment_discovered_count
from src.sources.base.models import IngestionSource

router = APIRouter(prefix="/documents", tags=["documents"])

class AddDiscoveredDocumentRequest(BaseModel):
    run_id: str
    source_instance_id: str
    content_checksum: str

@router.post("/add_discovered_document")
def add_discovered_document_endpoint(req: AddDiscoveredDocumentRequest):
    """
    Mark a document as discovered but not yet indexed.

    Args:
        run_id: The ID of the indexing run.
        source_instance_id: The source instance ID of the document.
        content_checksum: The checksum of the document content.

    Returns:
        Success message.
    """
    add_discovered_document(
        run_id=req.run_id,
        source_instance_id=req.source_instance_id,
        content_checksum=req.content_checksum,
    )
    increment_discovered_count(req.run_id)

    return {"status": "Document marked as discovered."}

@router.get("/{document_id}")
def get_document(document_id: str):
    """
    Retrieve document metadata by document ID.

    Args:
        document_id: The ID of the document to retrieve.

    Returns:
        Document metadata if found.

    Raises:
        HTTPException: If the document is not found.
    """
    query = "SELECT * FROM documents WHERE document_id = ?"
    document = get_document_from_db(document_id)
    
    if not document:
        raise HTTPException(status_code=404, detail=f"Document with ID {document_id} not found.")
    
    return document


@router.get("/{document_id}/open")
def get_open_descriptor(document_id: str):
    doc = get_document(document_id)   # fetch from documents table
    if doc is None:
        raise HTTPException(404, "Document not found")

    source_type, scope = retrieve_source(document_id)
    source = IngestionSource.from_scope(scope, should_stop=lambda: False)

    return source.get_open_descriptor(doc)

class BatchGetRequest(BaseModel):
    document_ids: list[str]

@router.post("/batch_get")
def batch_get_documents(req: BatchGetRequest):
    """
    Retrieve multiple documents by their IDs.

    Args:
        document_ids: List of document IDs to retrieve.

    Returns:
        List of document metadata.
    """
    documents = []
    for doc_id in req.document_ids:
        document = get_document_from_db(doc_id)
        if document:
            documents.append(document)
    
    return documents
