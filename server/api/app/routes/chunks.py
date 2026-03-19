from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from api.app.cache import distribution_cache

from loseme_core.models import Chunk
from storage.vector_db.runtime import get_vector_store

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


@router.get("/stats/distribution")
def get_chunk_distribution(chunker_name: str = None):
    """Return char_len distribution and chiunks-per-doc distribution for the given chunker filter."""
    from qdrant_client import QdrantClient
    import os, collections

    cache_key = f"distribution:{chunker_name or 'all'}"
    cached = distribution_cache.get(cache_key)
    if cached is not None:
        return cached

    client = QdrantClient(url=os.getenv("QDRANT_URL", "http://qdrant:6333"))
    COLLECTION = "chunks"

    # We also need source_path to compute chunks-per-doc
    char_lens = []
    chunks_per_doc = collections.Counter()

    # If filtering by chunker, we need to get the source_paths for those doc parts first
    allowed_paths = None
    if chunker_name and chunker_name != 'all':
        from storage.metadata_db.db import fetch_all
        rows = fetch_all(
            "SELECT source_path FROM document_parts WHERE chunker_name = ?",
            (chunker_name,)
        )
        allowed_paths = {row["source_path"] for row in rows}

    offset = None
    while True:
        result, next_offset = client.scroll(
            collection_name=COLLECTION,
            limit=500,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for point in result:
            path = point.payload.get("source_path", "unknown")
            if allowed_paths is not None and path not in allowed_paths:
                continue
            meta = point.payload.get("metadata", {})
            char_len = meta.get("char_len")
            if char_len is not None:
                char_lens.append(char_len)
            chunks_per_doc[path] += 1

    # filter chunks_per_doc too if needed
        if next_offset is None:
            break
        offset = next_offset

    if allowed_paths is not None:
        chunks_per_doc = collections.Counter({
            k: v for k, v in chunks_per_doc.items() if k in allowed_paths
        })

    # Build histogram buckets
    CHAR_BUCKETS  = [0, 100, 300, 600, 900, 1200, 2000, 9_999_999]
    CHAR_LABELS   = ['<100','100-300','300-600','600-900','900-1200','1200-2000','>2000']
    DOC_BUCKETS   = [0, 1, 5, 10, 20, 50, 100, 9_999_999]
    DOC_LABELS    = ['1','2-5','6-10','11-20','21-50','51-100','>100']

    def make_hist(data, buckets, labels):
        counts = [0] * len(labels)
        for v in data:
            for i in range(len(buckets) - 1):
                if buckets[i] <= v < buckets[i+1]:
                    counts[i] += 1
                    break
        return [{"label": l, "count": c} for l, c in zip(labels, counts)]

    doc_counts = list(chunks_per_doc.values())

    stats = {}
    if char_lens:
        s = sorted(char_lens)
        n = len(s)
        stats = {
            "count": n,
            "min": s[0], "max": s[-1],
            "mean": round(sum(s)/n, 1),
            "p50": s[n//2],
            "p95": s[int(n*0.95)],
        }

    result = {
        "char_len_histogram": make_hist(char_lens, CHAR_BUCKETS, CHAR_LABELS),
        "chunks_per_doc_histogram": make_hist(doc_counts, DOC_BUCKETS, DOC_LABELS),
        "stats": stats,
        "total_chunks": len(char_lens),
    }
    distribution_cache.set(cache_key, result)
    return result
