import json
import uuid
from datetime import datetime
from typing import Optional
from pathlib import Path

from storage.metadata_db.db import execute, fetch_one, fetch_all
from src.sources.base.models import IndexingRun, IndexingScope
from storage.metadata_db.processed_documents import get_all_processed
import logging
logger = logging.getLogger(__name__)

def _now() -> str:
    return datetime.utcnow().isoformat()

def add_monitored_source(source_type: str, scope: IndexingScope) -> str:
    source_id = str(uuid.uuid4())
    execute(
        """
        INSERT OR IGNORE INTO monitored_sources (
            id,
            source_type,
            locator,
            scope_json,
            last_seen_fingerprint,
            last_checked_at,
            last_ingested_at,
            enabled,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
        """,
        (
            source_id,
            source_type,
            scope.locator(),
            json.dumps(scope.serialize()),
            None,
            None,
            None,
            _now(),
        ),
    )

    logger.info(f"Added monitored source {source_id} of type {source_type} with locator {scope.locator}")
    return source_id

def get_monitored_source_by_id(source_id: str) -> Optional[dict]:
    row = fetch_one(
        """
        SELECT
            id,
            source_type,
            locator,
            scope_json,
            last_seen_fingerprint,
            last_checked_at,
            last_ingested_at,
            enabled,
            created_at
        FROM monitored_sources
        WHERE id = ?
        """,
        (source_id,),
    )
    if row is None:
        return None

    return {
        "id": row[0],
        "source_type": row[1],
        "locator": row[2],
        "scope": IndexingScope.deserialize(json.loads(row[3])),
        "last_seen_fingerprint": row[4],
        "last_checked_at": row[5],
        "last_ingested_at": row[6],
        "enabled": bool(row[7]),
        "created_at": row[8],
    }

def update_monitored_source_check_times(
    source_id: str,
    last_seen_fingerprint: Optional[str] = None,
    last_checked_at: Optional[str] = None,
    last_ingested_at: Optional[str] = None,
) -> None:
    fields = []
    params = []

    if last_seen_fingerprint is not None:
        fields.append("last_seen_fingerprint = ?")
        params.append(last_seen_fingerprint)
    if last_checked_at is not None:
        fields.append("last_checked_at = ?")
        params.append(last_checked_at)
    if last_ingested_at is not None:
        fields.append("last_ingested_at = ?")
        params.append(last_ingested_at)

    if not fields:
        return  # Nothing to update

    params.append(source_id)

    query = f"""
        UPDATE monitored_sources
        SET {', '.join(fields)}
        WHERE id = ?
    """

    execute(query, tuple(params))

def list_all_monitored_sources() -> list:
    rows = fetch_all(
        """
        SELECT
            id,
            source_type,
            locator,
            scope_json,
            last_seen_fingerprint,
            last_checked_at,
            last_ingested_at,
            enabled,
            created_at
        FROM monitored_sources
        """
    )

    logger.debug(f"Fetched {len(rows)} monitored sources from database.")
    sources = []
    for row in rows:
        sources.append({
            "id": row[0],
            "source_type": row[1],
            "locator": row[2],
            "scope": IndexingScope.deserialize(json.loads(row[3])),
            "last_seen_fingerprint": row[4],
            "last_checked_at": row[5],
            "last_ingested_at": row[6],
            "enabled": bool(row[7]),
            "created_at": row[8],
        })
    return sources
