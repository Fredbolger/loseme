from fastapi import HTTPException, APIRouter
from storage.metadata_db.document import get_document as get_document_from_db

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
        raise HTTPException(status_code=404, detail="Document not found")
    
    return document



