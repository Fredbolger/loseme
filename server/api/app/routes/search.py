from __future__ import annotations
 
import uuid
from typing import Any, Optional
 
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
 
from storage.metadata_db.search_sessions import (
    DEFAULT_CACHE_THRESHOLD,
    add_message,
    create_session,
    delete_session,
    find_similar_session,
    get_session,
    list_sessions,
    update_session_results,
)
from storage.vector_db.runtime import get_embedding_provider, get_vector_store
 
from .llm import build_chat_context, stream_llm_answer


router = APIRouter()

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class SearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=50)
    cache_threshold: float = Field(default=DEFAULT_CACHE_THRESHOLD, ge=0.0, le=1.0)


class ChatRequest(BaseModel):
    message: str
    top_k: int = Field(default=3, ge=1, le=20)  # for sub-search
 

class SessionSummary(BaseModel):
    session_id: str
    query: str
    result_count: int
    message_count: int
    updated_at: str
    cache_hit: bool = False
    cache_score: Optional[float] = None


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    search_results_used: list[str]
    created_at: str


class SessionDetail(BaseModel):
    session_id: str
    query: str
    result_ids: list[str]
    messages: list[MessageOut]
    created_at: str
    updated_at: str

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
 
def _run_vector_search(query_embedding: list[float], top_k: int) -> list[dict[str, Any]]:
    store = get_vector_store()
    # search returns a list of tuples (Chunk, score)
    return store.search(query_embedding, top_k=top_k)
 
 
def _background_refresh(session_id: str, query_embedding: list[float], top_k: int) -> None:
    """Re-run the search and update result_ids. Runs as a Celery task or BackgroundTask."""
    results = _run_vector_search(query_embedding, top_k)
    #result_ids = [r["document_part_id"] for r in results]
    result_ids = [r[0].document_part_id for r in results]
    update_session_results(session_id, result_ids)


# ---------------------------------------------------------------------------
# POST /search
# ---------------------------------------------------------------------------
 
@router.post("/search")
async def search(req: SearchRequest, background_tasks: BackgroundTasks) -> dict:
    embedder = get_embedding_provider()
    query_embedding = embedder.embed_query(req.query)
 
    # --- Semantic cache check ---
    cache_result = find_similar_session(query_embedding.dense, threshold=req.cache_threshold)
    if cache_result is not None:
        cached_session, score = cache_result
 
        # Return the cached answer immediately
        final_answer = next(
            (m.content for m in reversed(cached_session.messages) if m.role == "assistant"),
            None,
        )
 
        # Refresh in background so the cache stays current
        background_tasks.add_task(
            _background_refresh, cached_session.id, query_embedding, req.top_k
        )
 
        return {
            "session_id": cached_session.id,
            "results": cached_session.result_ids,
            "answer": final_answer,
            "cache_hit": True,
            "cache_score": round(score, 4),
        }
 
    # --- Cache miss: run fresh search ---
    raw_results = _run_vector_search(query_embedding, req.top_k)
    #result_ids = [r["document_part_id"] for r in raw_results]
    result_ids = [r[0].document_part_id for r in raw_results]
 
    # Create session
    session_id = uuid.uuid4().hex
    # query_embedding is expected to be list[float]
    # however, it is currently type EmbeddingOutput with attributes dense, sparse and colbert
    # for the purpose of matching, we use the dense attribute for now.  
    create_session(
        session_id=session_id,
        query=req.query,
        query_embedding=query_embedding.dense,
        result_ids=result_ids,
    )
 
    # Store user query as first message
    add_message(
        message_id=uuid.uuid4().hex,
        session_id=session_id,
        role="user",
        content=req.query,
    )
 
    # Generate initial LLM answer grounded in retrieved chunks
    context = build_chat_context(
        query=req.query,
        result_ids=result_ids,
        prior_messages=[],
    )
    answer = await stream_llm_answer(context)
 
    add_message(
        message_id=uuid.uuid4().hex,
        session_id=session_id,
        role="assistant",
        content=answer,
        search_results_used=result_ids,
    )
 
    return {
        "session_id": session_id,
        "results": result_ids,
        "answer": answer,
        "cache_hit": False,
        "cache_score": None,
    }

# ---------------------------------------------------------------------------
# GET /search/history
# ---------------------------------------------------------------------------
 
@router.get("/search/history")
def search_history(limit: int = 50, offset: int = 0) -> dict:
    sessions = list_sessions(limit=limit, offset=offset)
    return {
        "sessions": [
            SessionSummary(
                session_id=s.id,
                query=s.query,
                result_count=len(s.result_ids),
                message_count=0,  # not loaded here for performance
                updated_at=s.updated_at.isoformat(),
            ).model_dump()
            for s in sessions
        ]
    }
 
 
# ---------------------------------------------------------------------------
# GET /search/sessions/{session_id}
# ---------------------------------------------------------------------------
 
@router.get("/search/sessions/{session_id}")
def get_session_detail(session_id: str) -> dict:
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
 
    return SessionDetail(
        session_id=session.id,
        query=session.query,
        result_ids=session.result_ids,
        messages=[
            MessageOut(
                id=m.id,
                role=m.role,
                content=m.content,
                search_results_used=m.search_results_used,
                created_at=m.created_at.isoformat(),
            )
            for m in session.messages
        ],
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
    ).model_dump()
 
 
# ---------------------------------------------------------------------------
# POST /search/sessions/{session_id}/chat
# ---------------------------------------------------------------------------
 
@router.post("/search/sessions/{session_id}/chat")
async def chat(session_id: str, req: ChatRequest) -> dict:
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
 
    # Store user follow-up
    add_message(
        message_id=uuid.uuid4().hex,
        session_id=session_id,
        role="user",
        content=req.message,
    )
 
    # Sub-search: find chunks relevant to the follow-up question
    embedder = get_embedding_provider()
    follow_up_embedding = embedder.embed_query(req.message)
    sub_results = _run_vector_search(follow_up_embedding, req.top_k)
    sub_result_ids = [r["document_part_id"] for r in sub_results]
 
    # Merge with existing session result_ids (deduplicated)
    all_result_ids = list(dict.fromkeys(session.result_ids + sub_result_ids))
 
    # Build full context: original results + sub-search + prior messages
    prior_messages = [
        {"role": m.role, "content": m.content} for m in session.messages
    ]
    context = build_chat_context(
        query=req.message,
        result_ids=all_result_ids,
        prior_messages=prior_messages,
    )
    answer = await stream_llm_answer(context)
 
    add_message(
        message_id=uuid.uuid4().hex,
        session_id=session_id,
        role="assistant",
        content=answer,
        search_results_used=sub_result_ids,
    )
 
    return {
        "session_id": session_id,
        "answer": answer,
        "sub_search_result_ids": sub_result_ids,
    }
 
 
# ---------------------------------------------------------------------------
# DELETE /search/sessions/{session_id}
# ---------------------------------------------------------------------------
 
@router.delete("/search/sessions/{session_id}")
def remove_session(session_id: str) -> dict:
    deleted = delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": True, "session_id": session_id}
 

