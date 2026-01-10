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
    results = store.search(query_vector, top_k=req.top_k)

    # Print the results for debugging
    for r in results:
        print(f"Chunk ID: {r[0]}, Score: {r[1]}, Metadata: {r[2]}")

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

