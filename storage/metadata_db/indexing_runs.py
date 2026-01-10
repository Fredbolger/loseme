import json
import uuid
import hashlib
from datetime import datetime
from typing import Optional
from pathlib import Path

from storage.metadata_db.db import execute, fetch_one
from src.domain.models import IndexingRun, IndexingScope
from storage.metadata_db.processed_documents import get_all_processed
import logging
logger = logging.getLogger(__name__)

def _now() -> str:
    return datetime.utcnow().isoformat()


# ----------------------------
# Scope (de)serialization
# ----------------------------

def serialize_scope(scope: IndexingScope) -> dict:
    """
    Canonical serialization of IndexingScope.

    IMPORTANT:
    - Paths are resolved to absolute paths
    - Directories are sorted
    This guarantees stable equality across runs.
    """
    return {
        "directories": sorted(str(p.resolve()) for p in scope.directories),
        "include_patterns": sorted(scope.include_patterns),
        "exclude_patterns": sorted(scope.exclude_patterns),
    }


def deserialize_scope(data: dict) -> IndexingScope:
    return IndexingScope(
        directories=[Path(p) for p in data["directories"]],
        include_patterns=data.get("include_patterns", []),
        exclude_patterns=data.get("exclude_patterns", []),
    )


# ----------------------------
# Indexing runs
# ----------------------------

def create_run(
    source_type: str,
    scope: IndexingScope,
) -> IndexingRun:
    run_id = str(uuid.uuid4())
    now = _now()

    execute(
        """
        INSERT INTO indexing_runs (
            id,
            source_type,
            scope_json,
            status,
            last_document_id,
            started_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            source_type,
            json.dumps(serialize_scope(scope)),
            "running",
            None,
            now,
            now,
        ),
    )

    return IndexingRun(
        id=run_id,
        scope=scope,
        status="running",
        start_time=datetime.fromisoformat(now),
        updated_at=datetime.fromisoformat(now),
        last_document_id=None,
    )


def load_latest_run(
    source_type: str,
    scope: IndexingScope,
) -> Optional[IndexingRun]:
    """
    Load the latest indexing run for a given source type and scope.
    Returns None if no run exists.
    """
    row = fetch_one(
        """
        SELECT *
        FROM indexing_runs
        WHERE source_type = ?
          AND status != 'completed'
        ORDER BY started_at DESC
        LIMIT 1
        """,
        (
            source_type,
        ),
    )
    
    if not row:
        return None

    logger.info(
        "load_latest_run: source=%s → %s",
        source_type,
        "FOUND" if row else "NONE",
    )


    stored_scope = json.loads(row["scope_json"])
    run_id = row["id"]

    # ✅ Load processed documents for this run from DB
    processed_docs = get_all_processed(run_id)

    return IndexingRun(
        id=run_id,
        scope=deserialize_scope(stored_scope),
        status=row["status"],
        start_time=datetime.fromisoformat(row["started_at"]),
        processed_documents=processed_docs,        # <- checkpoint is now correct
        last_document_id=row["last_document_id"],  # optional, but recommended
    )

# ----------------------------
# Updates
# ----------------------------

def update_status(run_id: str, status: str) -> None:
    execute(
        """
        UPDATE indexing_runs
        SET status = ?, updated_at = ?
        WHERE id = ?
        """,
        (status, _now(), run_id),
    )


def update_checkpoint(run_id: str, source_instance_id: str) -> None:
    execute(
        """
        UPDATE indexing_runs
        SET last_document_id = ?, updated_at = ?
        WHERE id = ?
        """,
        (source_instance_id, _now(), run_id),
    )

