from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

from storage.vector_db.runtime import (
    get_vector_store,
    get_embedding_provider,
)

router = APIRouter(prefix="/search", tags=["search"])


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


@router.post("")
def search(req: SearchRequest):
    embedder = get_embedding_provider()
    store = get_vector_store()

    query_vector = embedder.embed(req.query)
    results = store.query(query_vector, top_k=req.top_k)

    return {
        "results": [
            {
                "chunk_id": chunk_id,
                "score": score,
                "metadata": metadata,
            }
            for chunk_id, score, metadata in results
        ]
    }

