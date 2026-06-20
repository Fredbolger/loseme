"""
Search session persistence with source storage.
"""

from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from storage.metadata_db.db import get_connection

DEFAULT_CACHE_THRESHOLD = 0.92

# Schema with title and sources columns
CREATE_SESSIONS_TABLE = """
CREATE TABLE IF NOT EXISTS search_sessions (
    id              TEXT PRIMARY KEY,
    query           TEXT NOT NULL,
    query_embedding BLOB NOT NULL,
    result_ids      TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    title           TEXT
);
"""

CREATE_MESSAGES_TABLE = """
CREATE TABLE IF NOT EXISTS session_messages (
    id                   TEXT PRIMARY KEY,
    session_id           TEXT NOT NULL REFERENCES search_sessions(id) ON DELETE CASCADE,
    role                 TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content              TEXT NOT NULL,
    search_results_used  TEXT,
    sources              TEXT,
    created_at           TEXT NOT NULL
);
"""

CREATE_SESSION_IDX = """
CREATE INDEX IF NOT EXISTS idx_session_messages_session_id
    ON session_messages(session_id);
"""

# Migrations for existing databases
ADD_TITLE_COLUMN = "ALTER TABLE search_sessions ADD COLUMN title TEXT;"
ADD_SOURCES_COLUMN = "ALTER TABLE session_messages ADD COLUMN sources TEXT;"


def init_search_history_schema() -> None:
    """Create tables if they don't exist. Safe to call on every startup."""
    with get_connection() as conn:
        # Create tables if they don't exist
        conn.execute(CREATE_SESSIONS_TABLE)
        conn.execute(CREATE_MESSAGES_TABLE)
        conn.execute(CREATE_SESSION_IDX)
        
        # Add title column to search_sessions if it doesn't exist
        try:
            conn.execute(ADD_TITLE_COLUMN)
        except sqlite3.OperationalError:
            # Column already exists
            pass
        
        # Add sources column to session_messages if it doesn't exist
        try:
            conn.execute(ADD_SOURCES_COLUMN)
        except sqlite3.OperationalError:
            # Column already exists
            pass
            
        conn.commit()


@dataclass
class SearchSession:
    id: str
    query: str
    query_embedding: list[float]
    result_ids: list[str]
    created_at: datetime
    updated_at: datetime
    title: Optional[str] = None
    messages: list[SessionMessage] = field(default_factory=list)
    message_count: int = 0  # ✅ Add this field for efficient counting


@dataclass
class SessionMessage:
    id: str
    session_id: str
    role: str
    content: str
    search_results_used: list[str]
    sources: list[dict]
    created_at: datetime


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
    # Safely get title column
    title = None
    try:
        if "title" in row.keys():
            title = row["title"]
    except (IndexError, KeyError):
        pass
    
    return SearchSession(
        id=row["id"],
        query=row["query"],
        query_embedding=json.loads(row["query_embedding"]),
        result_ids=json.loads(row["result_ids"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        title=title,
    )


def _row_to_message(row: sqlite3.Row) -> SessionMessage:
    # Safely get sources column
    sources = []
    try:
        if "sources" in row.keys() and row["sources"]:
            sources = json.loads(row["sources"])
    except (json.JSONDecodeError, TypeError, IndexError):
        sources = []
    
    # Safely get search_results_used
    search_results = []
    try:
        if "search_results_used" in row.keys() and row["search_results_used"]:
            search_results = json.loads(row["search_results_used"])
    except (json.JSONDecodeError, TypeError, IndexError):
        search_results = []
    
    return SessionMessage(
        id=row["id"],
        session_id=row["session_id"],
        role=row["role"],
        content=row["content"],
        search_results_used=search_results,
        sources=sources,
        created_at=datetime.fromisoformat(row["created_at"]),
    )


# ✅ NEW: Helper function to get message count efficiently
def get_message_count(session_id: str) -> int:
    """Get message count for a session without loading all messages."""
    with get_connection() as conn:
        result = conn.execute(
            "SELECT COUNT(*) FROM session_messages WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        return result[0] if result else 0


# ✅ NEW: Get counts for multiple sessions in one query
def get_message_counts(session_ids: list[str]) -> dict[str, int]:
    """Get message counts for multiple sessions in one query."""
    if not session_ids:
        return {}
    
    placeholders = ','.join(['?' for _ in session_ids])
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT session_id, COUNT(*) as count 
            FROM session_messages 
            WHERE session_id IN ({placeholders})
            GROUP BY session_id
            """,
            session_ids,
        ).fetchall()
        return {row[0]: row[1] for row in rows}


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
            INSERT INTO search_sessions (id, query, query_embedding, result_ids, created_at, updated_at, title)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                query,
                json.dumps(query_embedding),
                json.dumps(result_ids),
                now,
                now,
                None,
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
        title=None,
        message_count=0,  # New session has no messages yet
    )


def update_session_title(session_id: str, title: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE search_sessions SET title = ? WHERE id = ?",
            (title, session_id),
        )
        conn.commit()


def update_session_results(session_id: str, result_ids: list[str]) -> None:
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
    session.message_count = len(session.messages)  # ✅ Set message count
    return session


def list_sessions(limit: int = 50, offset: int = 0) -> list[SearchSession]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM search_sessions ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    
    sessions = [_row_to_session(r) for r in rows]
    
    # ✅ Get message counts efficiently
    session_ids = [s.id for s in sessions]
    message_counts = get_message_counts(session_ids)
    
    # ✅ Set message count for each session
    for session in sessions:
        session.message_count = message_counts.get(session.id, 0)
        # Don't load all messages for listing (performance)
        session.messages = []
    
    return sessions


def delete_session(session_id: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM search_sessions WHERE id = ?", (session_id,)
        )
        conn.commit()
    return cur.rowcount > 0


def find_similar_session(
    query_embedding: list[float],
    threshold: float = DEFAULT_CACHE_THRESHOLD,
) -> Optional[tuple[SearchSession, float]]:
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
        best_session.message_count = len(best_session.messages)  # ✅ Set message count
        return best_session, best_score

    return None


def add_message(
    message_id: str,
    session_id: str,
    role: str,
    content: str,
    search_results_used: list[str] | None = None,
    sources: list[dict] | None = None,
) -> SessionMessage:
    now = _now_iso()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO session_messages
                (id, session_id, role, content, search_results_used, sources, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message_id,
                session_id,
                role,
                content,
                json.dumps(search_results_used or []),
                json.dumps(sources or []),
                now,
            ),
        )
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
        sources=sources or [],
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
