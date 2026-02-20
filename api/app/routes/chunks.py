import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
from typing import List, Dict, Any

from src.sources.base.models import Chunk, Document, IngestionSource
from storage.metadata_db.document_parts import get_document_part_by_id
#from storage.metadata_db.document import retrieve_source
from storage.vector_db.runtime import get_vector_store

from src.core.wiring import build_chunker

router = APIRouter(prefix="/chunks", tags=["chunks"])

class ChunkMetadataResponse(BaseModel):
    chunk_id: str
    document_id: str
    device_id: str
    index: int
    metadata: Dict[str, Any]
    text: str

class ChunkIDsResponse(BaseModel):
    chunk_ids: List[str]

@router.get("/number_of_chunks", response_model=Dict[str, int])
def get_number_of_chunks() -> Dict[str, int]:
    """
    Retrieve the total number of chunks currently stored in the vector database.
    """
    store = get_vector_store()
    num_chunks = store.count_chunks()
    
    return {"number_of_chunks": num_chunks}

"""
@router.get("/{chunk_id}", response_model=ChunkMetadataResponse)
def get_chunk_metadata(chunk_id: str) -> ChunkMetadataResponse:
    '''
    Retrieve metadata and text for a specific chunk by its ID.
    
    Args:
        chunk_id: The unique identifier of the chunk.
        
    Returns:
        Metadata and text of the specified chunk.
    '''
    
    store = get_vector_store()
    chunker = build_chunker()

    chunk = store.retrieve_chunk_by_id(chunk_id)
    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")
    
    # Get the document row associated with the chunk from the database this will give us device_id without the unit locator
    # The unit locator is only relevant for processed_documents
    doc = get_document(chunk.document_id)
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Retrieve the actual document from the source including its text
    source_type, scope = retrieve_source(chunk.document_id)
    source = IngestionSource.from_scope(scope, should_stop=lambda: False)

    document = source.extract_by_document_id(document_id=chunk.document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document content not found")
    
    if document.is_multipart:
        try:
            chunks, chunk_texts = chunker.chunk_multipart(document, document.texts, unit_locator=document.unit_locators)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error during multipart chunking: {str(e)}")

    else:
        try:
            chunks, chunk_texts = chunker.chunk(document, document.texts[0], unit_locator=document.unit_locators[0])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error during chunking: {str(e)}")

    chunk_content = chunk_texts[chunk.index] if 0 <= chunk.index < len(chunk_texts) else ""
    return ChunkMetadataResponse(
        chunk_id=chunk.id,
        document_id=chunk.document_id,
        device_id=doc['device_id'],
        index=chunk.index,
        metadata=chunk.metadata,
        text=chunk_content
        )
"""

@router.get("/get_chunk_by_id/{chunk_id}", response_model=Chunk)
def get_chunk_by_id(chunk_id: str) -> Chunk:
    store = get_vector_store()
    chunk = store.retrieve_chunk_by_id(chunk_id)
    
    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")
    
    return Chunk(
        id=chunk.id,
        source_type=chunk.source_type,
        document_id=chunk.document_id,
        device_id=chunk.device_id,
        index=chunk.index,
        metadata=chunk.metadata,
        unit_locator=chunk.unit_locator
    )
