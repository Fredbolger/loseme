import json
import uuid
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
    
    NOTE: Currently only filters by source_type. Scope matching should be added
    to prevent resuming runs with different scopes.
    """
    # First, try to find a run with matching scope
    rows = fetch_all(
        """
        SELECT *
        FROM indexing_runs
        WHERE source_type = ?
         AND status IN ('pending', 'running', 'interrupted')
        ORDER BY started_at DESC
        """,
        (source_type,),
    )
    
    if not rows:
        return None
    
    # Find first run with matching scope
    target_scope_json = json.dumps(serialize_scope(scope))
    
    for row in rows:
        stored_scope_json = row["scope_json"]
        if stored_scope_json == target_scope_json:
            logger.info(
                "load_latest_run: source=%s, scope matches â†' resuming run %s",
                source_type,
                row["id"],
            )
            
            return IndexingRun(
                id=row["id"],
                scope=deserialize_scope(json.loads(stored_scope_json)),
                status=row["status"],
                start_time=datetime.fromisoformat(row["started_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                last_document_id=row["last_document_id"],
            )
    
    logger.info(
        "load_latest_run: source=%s â†' no matching scope found",
        source_type,
    )
    return None


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


# Helper function needed
def fetch_all(query: str, params: tuple = ()) -> list:
    """Fetch all rows - import from db module or define here"""
    from storage.metadata_db.db import fetch_all as _fetch_all
    return _fetch_all(query, params)
