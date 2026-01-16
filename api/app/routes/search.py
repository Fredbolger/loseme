from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any
from src.domain.models import Chunk

from storage.vector_db.runtime import (
    get_vector_store,
    get_embedding_provider,
)

router = APIRouter(prefix="/search", tags=["search"])


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class SearchResult(BaseModel):
    chunk_id: str
    document_id: str
    device_id: str
    score: float
    metadata: Dict[str, Any]


class SearchResponse(BaseModel):
    results: List[SearchResult]


@router.post("", response_model=SearchResponse)
def search(req: SearchRequest) -> SearchResponse:
    """
    Semantic search over indexed documents.
    
    Args:
        req: Search request with query text and top_k
        
    Returns:
        Search results with chunks, scores, and metadata
    """
    embedder = get_embedding_provider()
    store = get_vector_store()

    # Embed the query
    query_vector = embedder.embed_query(req.query)

    # Search returns List[Tuple[Chunk, float]]
    results = store.search(query_vector, top_k=req.top_k)

    # Transform to response format
    search_results = []
    for chunk, score in results:
        search_results.append(
            SearchResult(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                device_id=chunk.device_id,
                score=score,
                metadata=chunk.metadata,
            )
        )

    return SearchResponse(results=search_results)


