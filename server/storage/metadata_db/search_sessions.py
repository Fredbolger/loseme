"""
Search session persistence.

Stores search sessions (query + retrieved chunks) and their associated
chat messages. Also provides the semantic cache lookup: given a new query
embedding, find any existing session whose query embedding is above the
configured cosine-similarity threshold.
"""

from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from storage.metadata_db.db import get_connection  # reuse existing connection helper

# ---------------------------------------------------------------------------
# Similarity threshold for cache hits (override via env / config if needed)
# ---------------------------------------------------------------------------

DEFAULT_CACHE_THRESHOLD = 0.92


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

CREATE_SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS search_sessions (
    id              TEXT PRIMARY KEY,
    query           TEXT NOT NULL,
    query_embedding BLOB NOT NULL,   -- JSON-encoded list[float]
    result_ids      TEXT NOT NULL,   -- JSON-encoded list[str] (document_part_ids)
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
"""

CREATE_MESSAGES_TABLE = """
CREATE TABLE IF NOT EXISTS session_messages (
    id                   TEXT PRIMARY KEY,
    session_id           TEXT NOT NULL REFERENCES search_sessions(id) ON DELETE CASCADE,
    role                 TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content              TEXT NOT NULL,
    search_results_used  TEXT,        -- JSON-encoded list[str] (chunk_ids), nullable
    created_at           TEXT NOT NULL
);
"""

CREATE_SESSION_IDX = """
CREATE INDEX IF NOT EXISTS idx_session_messages_session_id
    ON session_messages(session_id);
"""


def init_search_history_schema() -> None:
    """Create tables if they don't exist. Safe to call on every startup."""
    with get_connection() as conn:
        conn.execute(CREATE_SESSIONS_TABLE)
        conn.execute(CREATE_MESSAGES_TABLE)
        conn.execute(CREATE_SESSION_IDX)
        conn.commit()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SearchSession:
    id: str
    query: str
    query_embedding: list[float]
    result_ids: list[str]
    created_at: datetime
    updated_at: datetime
    messages: list[SessionMessage] = field(default_factory=list)


@dataclass
class SessionMessage:
    id: str
    session_id: str
    role: str  # 'user' | 'assistant'
    content: str
    search_results_used: list[str]  # chunk_ids, may be empty
    created_at: datetime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cosine(a: list[float], b: list[float]) -> float:
    a = [float(x) for x in a]
    b = [float(x) for x in b]
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _row_to_session(row: sqlite3.Row) -> SearchSession:
    return SearchSession(
        id=row["id"],
        query=row["query"],
        query_embedding=json.loads(row["query_embedding"]),
        result_ids=json.loads(row["result_ids"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def _row_to_message(row: sqlite3.Row) -> SessionMessage:
    return SessionMessage(
        id=row["id"],
        session_id=row["session_id"],
        role=row["role"],
        content=row["content"],
        search_results_used=json.loads(row["search_results_used"] or "[]"),
        created_at=datetime.fromisoformat(row["created_at"]),
    )


# ---------------------------------------------------------------------------
# Session CRUD
# ---------------------------------------------------------------------------

def create_session(
    session_id: str,
    query: str,
    query_embedding: list[float],
    result_ids: list[str],
) -> SearchSession:
    now = _now_iso()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO search_sessions (id, query, query_embedding, result_ids, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                query,
                json.dumps(query_embedding),
                json.dumps(result_ids),
                now,
                now,
            ),
        )
        conn.commit()
    return SearchSession(
        id=session_id,
        query=query,
        query_embedding=query_embedding,
        result_ids=result_ids,
        created_at=datetime.fromisoformat(now),
        updated_at=datetime.fromisoformat(now),
    )


def update_session_results(session_id: str, result_ids: list[str]) -> None:
    """Called by the background refresh task after a cache hit."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE search_sessions SET result_ids = ?, updated_at = ? WHERE id = ?",
            (json.dumps(result_ids), _now_iso(), session_id),
        )
        conn.commit()


def get_session(session_id: str) -> Optional[SearchSession]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM search_sessions WHERE id = ?", (session_id,)
        ).fetchone()
    if row is None:
        return None
    session = _row_to_session(row)
    session.messages = list_messages(session_id)
    return session


def list_sessions(limit: int = 50, offset: int = 0) -> list[SearchSession]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM search_sessions ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    return [_row_to_session(r) for r in rows]


def delete_session(session_id: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM search_sessions WHERE id = ?", (session_id,)
        )
        conn.commit()
    return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Semantic cache lookup
# ---------------------------------------------------------------------------

def find_similar_session(
    query_embedding: list[float],
    threshold: float = DEFAULT_CACHE_THRESHOLD,
) -> Optional[tuple[SearchSession, float]]:
    """
    Scan all stored session embeddings and return the most similar session
    above `threshold`, or None if no cache hit.

    Returns (session, similarity_score) so callers can log / display confidence.

    Note: Linear scan is fine for hundreds of sessions. If history grows into
    the thousands, migrate session embeddings into a dedicated Qdrant collection.
    """
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM search_sessions ORDER BY updated_at DESC"
        ).fetchall()

    best_session: Optional[SearchSession] = None
    best_score = -1.0

    for row in rows:
        stored_embedding = json.loads(row["query_embedding"])
        score = _cosine(query_embedding, stored_embedding)
        if score > best_score:
            best_score = score
            best_session = _row_to_session(row)

    if best_session is not None and best_score >= threshold:
        best_session.messages = list_messages(best_session.id)
        return best_session, best_score

    return None


# ---------------------------------------------------------------------------
# Message CRUD
# ---------------------------------------------------------------------------

def add_message(
    message_id: str,
    session_id: str,
    role: str,
    content: str,
    search_results_used: list[str] | None = None,
) -> SessionMessage:
    now = _now_iso()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO session_messages
                (id, session_id, role, content, search_results_used, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                message_id,
                session_id,
                role,
                content,
                json.dumps(search_results_used or []),
                now,
            ),
        )
        # Bump session.updated_at so it surfaces at the top of history
        conn.execute(
            "UPDATE search_sessions SET updated_at = ? WHERE id = ?",
            (now, session_id),
        )
        conn.commit()
    return SessionMessage(
        id=message_id,
        session_id=session_id,
        role=role,
        content=content,
        search_results_used=search_results_used or [],
        created_at=datetime.fromisoformat(now),
    )


def list_messages(session_id: str) -> list[SessionMessage]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM session_messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        ).fetchall()
    return [_row_to_message(r) for r in rows]
