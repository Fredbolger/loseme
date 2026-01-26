import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
from typing import List, Dict, Any

from src.domain.models import Chunk, Document, IngestionSource
from storage.metadata_db.document import retrieve_source
from storage.vector_db.runtime import get_vector_store
from api.app.routes.documents import get_document

from src.core.wiring import build_chunker

router = APIRouter(prefix="/chunks", tags=["chunks"])

class ChunkMetadataResponse(BaseModel):
    chunk_id: str
    document_id: str
    device_id: str
    index: int
    metadata: Dict[str, Any]
    text: str

@router.get("/{chunk_id}", response_model=ChunkMetadataResponse)
def get_chunk_metadata(chunk_id: str) -> ChunkMetadataResponse:
    """
    Retrieve metadata and text for a specific chunk by its ID.
    
    Args:
        chunk_id: The unique identifier of the chunk.
        
    Returns:
        Metadata and text of the specified chunk.
    """
    
    store = get_vector_store()
    chunker = build_chunker()

    chunk = store.retrieve_chunk_by_id(chunk_id)
    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")
    
    # Get the document row associated with the chunk from the database
    doc = get_document(chunk.document_id)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Retrieve the actual document from the source
    source_type, scope = retrieve_source(chunk.document_id)
    source = IngestionSource.from_scope(scope, should_stop=lambda: False)

    document = source.extract_by_document_id(document_id=chunk.document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document content not found")

    chunks, chunk_texts = chunker.chunk(document, document.text)
    chunk_content = chunk_texts[chunk.index] if 0 <= chunk.index < len(chunk_texts) else ""
    return ChunkMetadataResponse(
        chunk_id=chunk.id,
        document_id=chunk.document_id,
        device_id=doc['device_id'],
        index=chunk.index,
        metadata=chunk.metadata,
        text=chunk_content
    )
