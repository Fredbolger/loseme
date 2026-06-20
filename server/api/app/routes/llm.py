"""
LLM integration for search sessions.

Keeps the LLM concern isolated from routing logic. The context builder
fetches chunk text from the metadata DB so the LLM answer is always
grounded in the actual retrieved documents.

Swap `_call_llm` for any backend (local Ollama, OpenAI-compatible API, etc.)
by changing only this file.

This module now provides FastAPI routes for server-side LLM execution,
allowing the client to trigger LLM calls that run on the server (which can
be configured to point to a separate LLM server, e.g., a GPU machine).
"""

from __future__ import annotations

import json
import os
from typing import Any, AsyncGenerator, Optional, List

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from storage.metadata_db.db import get_connection  # reuse existing connection
from storage.vector_db.runtime import get_vector_store

router = APIRouter(prefix="/llm", tags=["llm"])

# ---------------------------------------------------------------------------
# Config (set via environment, consistent with the rest of the project)
# ---------------------------------------------------------------------------

# LLM Server URL - can point to a separate machine (e.g., GPU server)
# Supports both LOSEME_LLM_URL (new) and OLLAMA_URL (backward compatible)
LLM_API_URL = os.getenv("LOSEME_LLM_URL") or os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
LLM_CHAT_URL = f"{LLM_API_URL}/api/chat"  # Ollama chat endpoint
LLM_GENERATE_URL = f"{LLM_API_URL}/api/generate"  # Ollama generate endpoint (streaming)

# Default model - can be overridden per-request
LLM_MODEL = os.getenv("LOSEME_LLM_MODEL", "mistral:7b")
LLM_TIMEOUT = float(os.getenv("LOSEME_LLM_TIMEOUT", "120"))

SYSTEM_PROMPT = """You are a helpful assistant for a local semantic search system.
The user has searched their personal documents. You are given the most relevant
document excerpts as context. Answer the user's question based only on the
provided context. If the context doesn't contain enough information, say so
clearly rather than guessing. Be concise and specific."""

# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------

class LLMGenerateRequest(BaseModel):
    """Request for server-side LLM generation with context"""
    session_id: Optional[str] = Field(default=None, description="Search session ID to associate the answer with (optional)")
    query: str = Field(..., description="User query")
    topK: int = Field(default=5, description="Number of top search results to use as context")
    result_ids: list[str] = Field(default_factory=list, description="Document part IDs from search results")
    context: Optional[str] = Field(default=None, description="Pre-built context string (optional)")
    model: str = Field(default=LLM_MODEL, description="Model to use")
    stream: bool = Field(default=True, description="Whether to stream the response")


class LLMHealthResponse(BaseModel):
    """Response for LLM health check"""
    status: str
    models: list[str] = Field(default_factory=list)
    url: str


# ---------------------------------------------------------------------------
# Helper: Test LLM Server Connection
# ---------------------------------------------------------------------------

async def test_llm_connection() -> LLMHealthResponse:
    """Test connection to the configured LLM server and fetch available models."""
    # List of URLs to try (configured URL first, then common defaults)
    urls_to_try = [LLM_API_URL]
    
    # Add common default URLs if not already in the list
    default_urls = [
        "http://localhost:11434",
        "http://host.docker.internal:11434",
        "http://127.0.0.1:11434",
    ]
    for url in default_urls:
        if url not in urls_to_try:
            urls_to_try.append(url)
    
    for url in urls_to_try:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = [m["name"] for m in data.get("models", [])]
                    return LLMHealthResponse(
                        status="ok",
                        models=models,
                        url=url
                    )
        except Exception:
            # Try next URL
            continue
    
    # If all URLs failed
    return LLMHealthResponse(
        status=f"error: Could not connect to any LLM server",
        models=[],
        url=LLM_API_URL
    )


# ---------------------------------------------------------------------------
# FastAPI Routes
# ---------------------------------------------------------------------------

@router.get("/health")
async def llm_health() -> LLMHealthResponse:
    """
    Check LLM server health and list available models.
    This allows the client to verify LLM connectivity separately from the API server.
    """
    return await test_llm_connection()


@router.get("/debug")
async def llm_debug() -> dict:
    """
    Debug endpoint to check LLM connectivity with verbose output.
    Useful for troubleshooting connection issues.
    """
    urls_tried = []
    errors = []
    generate_test_results = []
    
    urls_to_try = [LLM_API_URL]
    default_urls = [
        "http://localhost:11434",
        "http://host.docker.internal:11434",
        "http://127.0.0.1:11434",
    ]
    for url in default_urls:
        if url not in urls_to_try:
            urls_to_try.append(url)
    
    # First try to get models from /api/tags
    for url in urls_to_try:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = [m["name"] for m in data.get("models", [])]
                    return {
                        "status": "ok",
                        "working_url": url,
                        "models": models,
                        "urls_tried": urls_tried,
                        "errors": errors
                    }
                else:
                    urls_tried.append(url)
                    errors.append(f"{url}/api/tags: HTTP {response.status_code}")
        except Exception as e:
            urls_tried.append(url)
            errors.append(f"{url}/api/tags: {str(e)}")
    
    return {
        "status": "error",
        "urls_tried": urls_tried,
        "errors": errors,
        "configured_url": LLM_API_URL
    }


@router.get("/models")
async def get_llm_models() -> list[str]:
    """
    Get list of available models from the configured LLM server.
    """
    health = await test_llm_connection()
    return health.models


# ---------------------------------------------------------------------------
# Chunk text retrieval
# ---------------------------------------------------------------------------

def _retrieve_chunk_texts(chunk_ids: list[str]) -> dict[str, str]:
    store = get_vector_store()
    
    result = {}
    for chunk_id in chunk_ids:
        chunk = store.retrieve_chunk_by_id(chunk_id).text
        result[chunk_id] = chunk
    return result


# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------

def build_chat_context(
    query: str,
    result_ids: list[str],
    prior_messages: list[dict[str, str]],
) -> list[dict[str, str]]:
    """
    Build the message list to send to the LLM.

    Structure:
      system  → persona + instructions
      user    → context block (retrieved chunks)
      [prior messages replayed]
      user    → current query
    """
    chunk_texts = _retrieve_chunk_texts(result_ids)

    if chunk_texts:
        context_block = "\n\n---\n\n".join(
            f"[Document {i+1}]\n{text}"
            for i, (_, text) in enumerate(chunk_texts.items())
        )
        context_message = {
            "role": "user",
            "content": f"Here are the relevant document excerpts:\n\n{context_block}",
        }
        context_reply = {
            "role": "assistant",
            "content": "I have read the provided document excerpts and will use them to answer your questions.",
        }
        preamble = [context_message, context_reply]
    else:
        preamble = []

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(preamble)
    messages.extend(prior_messages)
    messages.append({"role": "user", "content": query})

    return messages


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

async def stream_llm_answer(messages: list[dict[str, str]]) -> str:
    """
    Call the configured LLM and return the full response as a string.

    Currently uses Ollama's /api/chat endpoint. To use a different backend:
    - OpenAI / OpenAI-compatible: swap the URL and payload format.
    - Local transformers: replace this function entirely.

    Streaming is consumed here and returned as a complete string so the
    rest of the system stays simple. Add true streaming to the route later
    if the web client needs it (Server-Sent Events or WebSocket).
    """
    payload = {
        "model": LLM_MODEL,
        "messages": messages,
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
        resp = await client.post(LLM_API_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()

    # Ollama response shape: {"message": {"role": "assistant", "content": "..."}}
    # Adjust for other backends as needed.
    return data["message"]["content"].strip()


# ---------------------------------------------------------------------------
# Server-Side LLM Generation with Streaming
# ---------------------------------------------------------------------------

async def _stream_ollama_response(
    model: str,
    prompt: str,
    stream: bool = True
) -> AsyncGenerator[str, None]:
    """
    Stream response from Ollama API.
    Yields chunks of text as they arrive.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": stream,
    }
    
    async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
        try:
            if stream:
                # Streaming mode - use client.stream()
                async with client.stream("POST", LLM_GENERATE_URL, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                if "response" in data:
                                    yield data["response"]
                            except json.JSONDecodeError:
                                # Skip malformed lines
                                continue
            else:
                # Non-streaming mode - use regular post
                response = await client.post(LLM_GENERATE_URL, json=payload)
                response.raise_for_status()
                data = response.json()
                # Yield the full response as a single chunk
                if "response" in data:
                    yield data["response"]
        except httpx.HTTPStatusError as e:
            try:
                error_text = e.response.text
            except:
                error_text = "No error text available"
            raise HTTPException(
                status_code=502,
                detail=f"LLM server error: {e.response.status_code} - {error_text}"
            )
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            raise HTTPException(
                status_code=500,
                detail=f"LLM generation failed: {str(e)}\n{tb}"
            )


async def _stream_chat_response(
    model: str,
    messages: list[dict[str, str]]
) -> AsyncGenerator[str, None]:
    """
    Stream response from Ollama Chat API.
    Yields chunks of text as they arrive.
    """
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
    }
    
    async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
        try:
            async with client.stream("POST", LLM_CHAT_URL, json=payload) as response:
                response.raise_for_status()
                buffer = ""
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                chunk = data["message"]["content"]
                                if chunk:
                                    # Handle partial JSON chunks
                                    buffer += chunk
                                    # Try to yield complete sentences or reasonable chunks
                                    # This is a simple approach - for production, consider better chunking
                                    if chunk in ['.', '?', '!', '\n'] or len(buffer) > 100:
                                        yield buffer
                                        buffer = ""
                        except json.JSONDecodeError:
                            continue
                # Yield any remaining buffer
                if buffer:
                    yield buffer
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=502,
                detail=f"LLM server error: {e.response.status_code} - {e.response.text}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"LLM generation failed: {str(e)}"
            )


def build_prompt_from_context(query: str, context: str) -> str:
    """Build a prompt for the generate endpoint from context and query."""
    return f"""{SYSTEM_PROMPT}

Context from documents:
{context}

Question: {query}

Answer:"""


@router.post("/generate")
async def generate_llm(
    request: LLMGenerateRequest,
    raw_request: Request
) -> StreamingResponse:
    """
    Generate LLM response server-side with streaming.
    
    The client receives a stream of text chunks. This allows:
    - LLM execution to continue even if the client disconnects
    - Separation of API server (can run on Raspberry Pi) from LLM server (can run on GPU machine)
    
    The context should be pre-built by the client using search results,
    or the client can provide result_ids and let the server build context.
    """
    model = request.model or LLM_MODEL
    
    # Build prompt
    if request.context:
        prompt = build_prompt_from_context(request.query, request.context)
    elif request.result_ids:
        # Fetch chunk texts from vector store
        try:
            store = get_vector_store()
            chunk_texts = []
            for chunk_id in request.result_ids[:request.topK]:
                try:
                    chunk = store.retrieve_chunk_by_id(chunk_id)
                    if chunk and chunk.text:
                        chunk_texts.append(chunk.text)
                except Exception:
                    continue
            
            if chunk_texts:
                context = "\n\n---\n\n".join(
                    f"[Document {i+1}]\n{text}" 
                    for i, text in enumerate(chunk_texts)
                )
                prompt = build_prompt_from_context(request.query, context)
            else:
                # No chunks found, use query directly
                prompt = f"{SYSTEM_PROMPT}\n\nQuestion: {request.query}\n\nAnswer:"
        except Exception as e:
            # If vector store fails, use query directly
            prompt = f"{SYSTEM_PROMPT}\n\nQuestion: {request.query}\n\nAnswer:"
    else:
        # No context provided, use query directly
        prompt = f"{SYSTEM_PROMPT}\n\nQuestion: {request.query}\n\nAnswer:"
    
    # Use streaming mode from request
    use_stream = getattr(request, 'stream', True)
    
    # Create streaming generator
    async def generate():
        try:
            async for chunk in _stream_ollama_response(model, prompt, stream=use_stream):
                # Format as SSE (Server-Sent Events)
                yield f"data: {json.dumps({'token': chunk})}\n\n"
            # Send completion marker
            yield "data: [DONE]\n\n"
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            yield f"data: {json.dumps({'error': str(e), 'traceback': tb})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Expose-Headers": "*",
        }
    )


@router.post("/generate-nostream")
async def generate_llm_no_stream(request: LLMGenerateRequest) -> dict:
    """
    Generate LLM response server-side without streaming (for compatibility).
    
    Returns the complete response at once.
    """
    model = request.model or LLM_MODEL
    
    # Build prompt (same logic as streaming version)
    if request.context:
        prompt = build_prompt_from_context(request.query, request.context)
    elif request.result_ids:
        store = get_vector_store()
        chunk_texts = []
        for chunk_id in request.result_ids[:10]:
            try:
                chunk = store.retrieve_chunk_by_id(chunk_id)
                if chunk and chunk.text:
                    chunk_texts.append(chunk.text)
            except Exception:
                continue
        
        context = "\n\n---\n\n".join(
            f"[Document {i+1}]\n{text}" 
            for i, text in enumerate(chunk_texts)
        )
        prompt = build_prompt_from_context(request.query, context)
    else:
        prompt = f"{SYSTEM_PROMPT}\n\nQuestion: {request.query}\n\nAnswer:"
    
    # Non-streaming call
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    
    try:
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
            response = await client.post(LLM_GENERATE_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            full_response = data.get("response", "")
            
            return {
                "response": full_response,
                "model": model,
                "done": True
            }
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"LLM server error: {e.response.status_code}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"LLM generation failed: {str(e)}"
        )

LLMGenerateRequest.model_rebuild()
