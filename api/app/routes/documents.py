from fastapi import HTTPException, APIRouter
from storage.metadata_db.document import get_document_by_id as get_document_from_db
from storage.metadata_db.document import retrieve_source
from src.domain.models import IngestionSource

router = APIRouter(prefix="/documents", tags=["documents"])
    
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
