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
    update_session_title,
)
from storage.vector_db.runtime import get_embedding_provider, get_vector_store

router = APIRouter()

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=50)
    cache_threshold: float = Field(default=DEFAULT_CACHE_THRESHOLD, ge=0.0, le=1.0)
    session_id: Optional[str] = None


class ChatRequest(BaseModel):
    session_id: str
    message: str
    top_k: int = Field(default=10, ge=1, le=50)


class SessionSummary(BaseModel):
    session_id: str
    query: str
    result_count: int
    message_count: int
    updated_at: str
    cache_hit: bool = False
    cache_score: Optional[float] = None
    title: Optional[str] = None


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    search_results_used: list[str] = []  # document_part_ids
    sources: list[dict] = []  # Store full source metadata
    created_at: str


class SessionDetail(BaseModel):
    session_id: str
    query: str
    result_ids: list[str]
    messages: list[MessageOut]
    created_at: str
    updated_at: str
    title: Optional[str] = None

class SearchResponseStore(BaseModel):
    """Optional assistant response to store for vector search mode"""
    assistant_response: Optional[str] = None
    sources: Optional[list[dict]] = None


# Moved StoreAnswerRequest here to avoid NameError
class StoreAnswerRequest(BaseModel):
    answer: str
    search_results_used: Optional[list[str]] = None
    sources: Optional[list[dict]] = None

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_vector_search(query_embedding, top_k: int) -> list[dict[str, Any]]:
    """Run vector search and return results with chunk_text included."""
    store = get_vector_store()
    raw = store.search(query_embedding, top_k=top_k)

    results = []
    for chunk, score in raw:
        results.append({
            "chunk_id": chunk.id,
            "document_part_id": chunk.document_part_id,
            "device_id": chunk.device_id,
            "score": score,
            "metadata": chunk.metadata or {},
            "source_path": chunk.source_path,
            "source_type": chunk.source_type,
            "unit_locator": chunk.unit_locator,
            "chunk_text": chunk.text or "",
        })
    return results


def _background_refresh(session_id: str, query_embedding, top_k: int) -> None:
    """Re-run the search and update stored result_ids."""
    results = _run_vector_search(query_embedding, top_k)
    result_ids = [r["document_part_id"] for r in results]
    update_session_results(session_id, result_ids)


def _build_full_conversation_context(messages: list, current_query: str) -> str:
    """Build complete conversation context from all message history."""
    context_parts = []
    
    for msg in messages:
        if msg.role == "user":
            context_parts.append(f"User: {msg.content}")
        elif msg.role == "assistant":
            # Include assistant responses for context
            context_parts.append(f"Assistant: {msg.content[:1000]}")  # Limit length
    
    context_parts.append(f"User: {current_query}")
    
    return "\n".join(context_parts)


def _format_sources_for_storage(results: list[dict]) -> list[dict]:
    """Format search results for storage."""
    return [
        {
            "document_part_id": r["document_part_id"],
            "source_path": r.get("source_path", ""),
            "score": r["score"],
            "chunk_text": r.get("chunk_text", "")[:500],  # Store preview
        }
        for r in results[:10]
    ]


# ---------------------------------------------------------------------------
# POST /search  — main search endpoint
# ---------------------------------------------------------------------------

@router.post("/search")
async def search(req: SearchRequest, background_tasks: BackgroundTasks) -> dict:
    embedder = get_embedding_provider()
    query_embedding = embedder.embed_query(req.query)

    # If continuing existing session
    if req.session_id:
        session = get_session(req.session_id)
        if session:
            # Run fresh search
            results = _run_vector_search(query_embedding, req.top_k)
            
            # Store user message with sources
            sources = _format_sources_for_storage(results)
            add_message(
                message_id=uuid.uuid4().hex,
                session_id=req.session_id,
                role="user",
                content=req.query,
                search_results_used=[r["document_part_id"] for r in results],
                sources=sources,
            )
            
            return {
                "session_id": req.session_id,
                "results": results,
                "cache_hit": False,
                "cache_score": None,
                "is_continuation": True,
            }

    # --- Semantic cache check for new sessions ---
    cache_result = find_similar_session(query_embedding.dense, threshold=req.cache_threshold)
    if cache_result is not None:
        cached_session, score = cache_result

        background_tasks.add_task(
            _background_refresh, cached_session.id, query_embedding, req.top_k
        )

        results = _run_vector_search(query_embedding, req.top_k)

        return {
            "session_id": cached_session.id,
            "results": results,
            "cache_hit": True,
            "cache_score": round(score, 4),
            "is_continuation": False,
        }

    # --- Cache miss: run fresh search ---
    results = _run_vector_search(query_embedding, req.top_k)
    result_ids = list(dict.fromkeys(r["document_part_id"] for r in results))

    session_id = uuid.uuid4().hex
    create_session(
        session_id=session_id,
        query=req.query,
        query_embedding=query_embedding.dense,
        result_ids=result_ids,
    )

    # Store user message with sources
    sources = _format_sources_for_storage(results)
    add_message(
        message_id=uuid.uuid4().hex,
        session_id=session_id,
        role="user",
        content=req.query,
        search_results_used=result_ids,
        sources=sources,
    )

    return {
        "session_id": session_id,
        "results": results,
        "cache_hit": False,
        "cache_score": None,
        "is_continuation": False,
    }


# ----------------------------------------------------------------------------
# POST /search/sessions/{session_id}/vector_result  — store vector search result
# ----------------------------------------------------------------------------

@router.post("/search/sessions/{session_id}/vector_result")
def store_vector_result(session_id: str, req: StoreAnswerRequest) -> dict:
    """Store vector search result as assistant message."""
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    add_message(
        message_id=uuid.uuid4().hex,
        session_id=session_id,
        role="assistant",
        content=req.answer,
        search_results_used=req.search_results_used or [],
        sources=req.sources or [],
    )
    
    return {"stored": True}

# ---------------------------------------------------------------------------
# POST /search/chat  — chat endpoint with full conversation context
# ---------------------------------------------------------------------------

@router.post("/search/chat")
async def chat(req: ChatRequest) -> dict:
    """Handle chat messages with full conversation context."""
    embedder = get_embedding_provider()
    query_embedding = embedder.embed_query(req.message)
    
    # Get existing session
    session = get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Run vector search with previous context
    results = _run_vector_search(query_embedding, req.top_k)
    
    # Store user message with sources
    sources = _format_sources_for_storage(results)
    add_message(
        message_id=uuid.uuid4().hex,
        session_id=req.session_id,
        role="user",
        content=req.message,
        search_results_used=[r["document_part_id"] for r in results],
        sources=sources,
    )
    
    # Build full conversation context from all messages
    full_conversation_context = _build_full_conversation_context(session.messages, req.message)
    
    # Update result_ids with new search results
    result_ids = list(dict.fromkeys(r["document_part_id"] for r in results))
    update_session_results(req.session_id, result_ids)
    
    # Also return stored sources from previous messages for context
    previous_sources = []
    for msg in session.messages:
        if msg.role == "assistant" and hasattr(msg, 'sources') and msg.sources:
            previous_sources.extend(msg.sources)
    
    return {
        "session_id": req.session_id,
        "results": results,
        "conversation_context": full_conversation_context,
        "previous_sources": previous_sources[:20],  # Limit to last 20 sources
    }


# ---------------------------------------------------------------------------
# POST /search/sessions/{session_id}/answer  — store LLM answer
# ---------------------------------------------------------------------------

@router.post("/search/sessions/{session_id}/answer")
def store_answer(session_id: str, req: StoreAnswerRequest) -> dict:
    """Store LLM answer in the session history."""
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    add_message(
        message_id=uuid.uuid4().hex,
        session_id=session_id,
        role="assistant",
        content=req.answer,
        search_results_used=req.search_results_used or session.result_ids,
        sources=req.sources or [],
    )
    
    # Update session title from first query if not set
    if not session.title:
        messages = session.messages
        if messages and messages[0].role == "user":
            first_query = messages[0].content
            title = first_query[:50] + ("..." if len(first_query) > 50 else "")
            try:
                update_session_title(session_id, title)
            except Exception:
                pass
    
    return {"stored": True}


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
                message_count=s.message_count,  # ✅ Now this will have the correct count!
                updated_at=s.updated_at.isoformat(),
                title=s.title or s.query[:50],
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
                sources=getattr(m, 'sources', []),
                created_at=m.created_at.isoformat(),
            )
            for m in session.messages
        ],
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
        title=session.title or session.query[:50],
    ).model_dump()


# ---------------------------------------------------------------------------
# DELETE /search/sessions/{session_id}
# ---------------------------------------------------------------------------

@router.delete("/search/sessions/{session_id}")
def remove_session(session_id: str) -> dict:
    deleted = delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": True, "session_id": session_id}
