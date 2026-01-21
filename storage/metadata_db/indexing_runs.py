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
# Indexing runs
# ----------------------------

def create_run(
    source_type: str,
    scope: IndexingScope,
) -> IndexingRun:
    """
    Create a new indexing run for the given source type and scope.
    """

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
            updated_at,
            discovered_document_count,
            indexed_document_count,
            stop_requested
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 0)
        """,
        (
            run_id,
            source_type,
            json.dumps(scope.serialize()),
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
        discovered_document_count=0, 
        indexed_document_count=0,
        stop_requested=False
    )

def load_latest_run_by_scope(
    scope: IndexingScope,
) -> Optional[IndexingRun]:
    """
    Load the latest indexing run for a given source type and scope.
    Returns None if no run exists.
    
    NOTE: Currently only filters by source_type. Scope matching should be added
    to prevent resuming runs with different scopes.
    """
    source_type = scope.type
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
    target_scope_json = json.dumps(scope.serialize())
    
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
                scope=IndexingScope.deserialize(json.loads(stored_scope_json)),
                status=row["status"],
                start_time=datetime.fromisoformat(row["started_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                last_document_id=row["last_document_id"],
                discovered_document_count=row["discovered_document_count"],
                indexed_document_count=row["indexed_document_count"],
                stop_requested=bool(row["stop_requested"]),
            )
    
    logger.info(
        "load_latest_run: source=%s â†' no matching scope found",
        source_type,
    )
    return None


def load_latest_run_by_type(
    source_type: str,
) -> Optional[IndexingRun]:
    """
    Load the latest indexing run for a given source type.
    Returns None if no run exists.
    """
    row = fetch_one(
        """
        SELECT *
        FROM indexing_runs
        WHERE source_type = ?
         AND status IN ('pending', 'running', 'interrupted')
        ORDER BY started_at DESC
        LIMIT 1
        """,
        (source_type,),
    )

    if row is None:
        return None

    return IndexingRun(
        id=row["id"],
        scope=IndexingScope.deserialize(json.loads(row["scope_json"])),
        status=row["status"],
        start_time=datetime.fromisoformat(row["started_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        last_document_id=row["last_document_id"],
        discovered_document_count=row["discovered_document_count"],
        indexed_document_count=row["indexed_document_count"],
        stop_requested=bool(row["stop_requested"]),
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

# Helper function needed
def fetch_all(query: str, params: tuple = ()) -> list:
    """Fetch all rows - import from db module or define here"""
    from storage.metadata_db.db import fetch_all as _fetch_all
    return _fetch_all(query, params)

# ----------------------------
# Run status
# ----------------------------

def show_runs(truncate_completed: bool = True) -> list[IndexingRun]:
    """
    Retrieve all indexing runs, optionally ignoring all but the most recent completed run.
    """
    rows = fetch_all(
        """
        SELECT *
        FROM indexing_runs
        ORDER BY started_at DESC
        """,
    )

    runs = []
    completed_found = False

    for row in rows:
        if truncate_completed and row["status"] == "completed":
            if completed_found:
                continue
            completed_found = True

        runs.append(
            IndexingRun(
                id=row["id"],
                scope=IndexingScope.deserialize(json.loads(row["scope_json"])),
                status=row["status"],
                start_time=datetime.fromisoformat(row["started_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                last_document_id=row["last_document_id"],
                discovered_document_count=row["discovered_document_count"],
                indexed_document_count=row["indexed_document_count"],
                stop_requested=bool(row["stop_requested"]),
            )
        )

    return runs

def request_stop(run_id: str) -> None:
    execute(
        """
        UPDATE indexing_runs
        SET stop_requested = 1, updated_at = ?
        WHERE id = ? AND status = 'running'
        """,
        (_now(), run_id),
    )

def is_stop_requested(run_id: str) -> bool:
    row = fetch_one(
        """
        SELECT stop_requested
        FROM indexing_runs
        WHERE id = ?
        """,
        (run_id,),
    )
    if row is None:
        raise ValueError(f"Indexing run with ID {run_id} not found.")
    return bool(row["stop_requested"])

def load_latest_interrupted(
    source_type: str,
) -> Optional[IndexingRun]:
    """
    Load the latest interrupted indexing run for a given source type.
    Returns None if no interrupted run exists.
    """
    logger.debug(f"Loading latest interrupted run for source type: {source_type}")

    row = fetch_one(
        """
        SELECT *
        FROM indexing_runs
        WHERE source_type = ?
         AND status = 'interrupted'
        ORDER BY started_at DESC
        LIMIT 1
        """,
        (source_type,),
    )

    if row is None:
        logger.debug(f"No interrupted run found for source type: {source_type}")
        # For now print the entire table for debugging
        all_rows = fetch_all("SELECT * FROM indexing_runs")
        pretty_rows = [dict(r) for r in all_rows]
    
        logger.debug(f"All indexing runs: {pretty_rows}")
        return None

    return IndexingRun(
        id=row["id"],
        scope=IndexingScope.deserialize(json.loads(row["scope_json"])),
        status=row["status"],
        start_time=datetime.fromisoformat(row["started_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        last_document_id=row["last_document_id"],
        discovered_document_count=row["discovered_document_count"],
        indexed_document_count=row["indexed_document_count"],
        stop_requested=bool(row["stop_requested"]),
    )

def load_run_by_id(
    run_id: str,
) -> Optional[IndexingRun]:
    """
    Load an indexing run by its ID.
    Returns None if no run exists.
    """
    row = fetch_one(
        """
        SELECT *
        FROM indexing_runs
        WHERE id = ?
        """,
        (run_id,),
    )

    if row is None:
        return None

    return IndexingRun(
        id=row["id"],
        scope=IndexingScope.deserialize(json.loads(row["scope_json"])),
        status=row["status"],
        start_time=datetime.fromisoformat(row["started_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        last_document_id=row["last_document_id"],
        discovered_document_count=row["discovered_document_count"],
        indexed_document_count=row["indexed_document_count"],
        stop_requested=bool(row["stop_requested"]),
    )

def set_run_resume(run_id: str) -> None:
    execute(
        """
        UPDATE indexing_runs
        SET stop_requested = 0, updated_at = ?
        WHERE id = ?
        """,
        (_now(), run_id)
    )
