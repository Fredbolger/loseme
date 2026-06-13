"""
LLM integration for search sessions.

Keeps the LLM concern isolated from routing logic. The context builder
fetches chunk text from the metadata DB so the LLM answer is always
grounded in the actual retrieved documents.

Swap `_call_llm` for any backend (local Ollama, OpenAI-compatible API, etc.)
by changing only this file.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from storage.metadata_db.db import get_connection  # reuse existing connection
from storage.vector_db.runtime import get_vector_store

# ---------------------------------------------------------------------------
# Config (set via environment, consistent with the rest of the project)
# ---------------------------------------------------------------------------

LLM_API_URL = os.getenv("LOSEME_LLM_URL", "http://localhost:11434/api/chat")
LLM_MODEL = os.getenv("LOSEME_LLM_MODEL", "llama3")
LLM_TIMEOUT = float(os.getenv("LOSEME_LLM_TIMEOUT", "60"))

SYSTEM_PROMPT = """You are a helpful assistant for a local semantic search system.
The user has searched their personal documents. You are given the most relevant
document excerpts as context. Answer the user's question based only on the
provided context. If the context doesn't contain enough information, say so
clearly rather than guessing. Be concise and specific."""


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
