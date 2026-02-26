from src.sources.base.models import IndexingScope
from src.sources.base.registry import indexing_scope_registry
from storage.metadata_db.db import execute, fetch_one, fetch_all
from typing import Optional, List, Tuple
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
def upsert_document_part(
    part: dict,
    run_id: Optional[str] = None,
) -> None:
    """
    Insert or update a document part in the database.
    If a part with the same document_part_id already exists, it will be updated with the new information.
    """

    execute(
        """
        INSERT INTO document_parts (
            document_part_id,
            checksum,
            source_type,
            source_instance_id,
            device_id,
            source_path,
            metadata_json,
            last_indexed_run_id,
            chunk_ids,
            unit_locator,
            content_type,
            extractor_name,
            extractor_version,
            created_at,
            updated_at,
            last_indexed_at,
            scope_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(document_part_id) DO UPDATE SET
            source_path = excluded.source_path,
            metadata_json = excluded.metadata_json,
            last_indexed_run_id = excluded.last_indexed_run_id,
            chunk_ids = excluded.chunk_ids,
            unit_locator = excluded.unit_locator,
            content_type = excluded.content_type,
            extractor_name = excluded.extractor_name,
            extractor_version = excluded.extractor_version,
            updated_at = excluded.updated_at,
            scope_json = excluded.scope_json
        """,
        (
            part["document_part_id"],
            part["checksum"],
            part["source_type"],
            part["source_instance_id"],
            part["device_id"],
            part["source_path"],
            json.dumps(part.get("metadata", {})),
            run_id,
            None,
            part.get("unit_locator"),
            part.get("content_type"),
            part.get("extractor_name"),
            part.get("extractor_version"),
            datetime.fromisoformat(part["created_at"]).isoformat(),
            datetime.fromisoformat(part["updated_at"]).isoformat(),
            None,
            json.dumps(part.get("scope_json"))
        ),

    )

def get_document_part_by_id(document_part_id: str) -> Optional[dict]:
    row = fetch_one(
        "SELECT * FROM document_parts WHERE document_part_id = ?",
        (document_part_id,),
    )
    if row:
        return dict(row) if row else None
    else:
        return None

def retrieve_scope_by_document_part_id(document_part_id: str) -> Optional[Tuple[str, IndexingScope]]:
    row = fetch_one(
        """
        SELECT
            source_type,
            source_instance_id,
            checksum,
            scope_json
        FROM document_parts
        WHERE document_part_id = ?
        """,
        (document_part_id,),
    )
    if row:
        source_type = row["source_type"]
        source_instance_id = row["source_instance_id"]
        checksum = row["checksum"]
        scope = indexing_scope_registry.deserialize(json.loads(row["scope_json"]))
        return source_type, scope
    return None

def mark_document_part_processed(document_part_id: str, run_id: str, chunk_ids: Optional[List[str]] = None, timestamp: Optional[str] = None) -> None:
    if timestamp is None:
        timestamp = datetime.utcnow().isoformat()

    if chunk_ids:
        execute(
            """
            UPDATE document_parts
            SET last_indexed_run_id = ?,
                chunk_ids = ?,
                last_indexed_at = ?,
                updated_at = ?
            WHERE document_part_id = ?
            """,
            (
                run_id,
                json.dumps(chunk_ids),
                timestamp,
                timestamp,
                document_part_id
            ),
        )
    if not chunk_ids:
        # If no chunk IDs provided, just update the last indexed info without changing chunk_ids
        execute(
            """
            UPDATE document_parts
            SET last_indexed_run_id = ?,
                last_indexed_at = ?,
                updated_at = ?
            WHERE document_part_id = ?
            """,
            (
                run_id,
                timestamp,
                timestamp,
                document_part_id
            ),
        )

def get_all_document_parts_by_source_instance_id(source_instance_id: str) -> List[dict]:
    rows = fetch_all(
        "SELECT * FROM document_parts WHERE source_instance_id = ?",
        (source_instance_id,),
    )
    return [dict(row) for row in rows]


def get_all_document_part_ids():
    rows = fetch_all(
        "SELECT document_part_id FROM document_parts",
    )
    return [row["document_part_id"] for row in rows]

def get_stale_parts(run_id: str):
    # Find all document parts with the same scope_json as the given run_id that have not been indexed in this run
    scope_json = fetch_one(
        "SELECT scope_json FROM indexing_runs WHERE id = ?",
        (run_id,),
    )["scope_json"]

    logger.debug(
        "Finding stale parts for run_id %s with scope_json %s",
        run_id,
        json.dumps(scope_json),
    )
    # for debugging, log all document parts with the same run_id
    all_parts = fetch_all(
        """
        SELECT document_part_id, last_indexed_run_id, chunk_ids
        FROM document_parts
        WHERE last_indexed_run_id = ?
        """,
        (run_id,),
    )
 
    rows = fetch_all(
        """
        SELECT dp.document_part_id, dp.chunk_ids
        FROM document_parts dp
        JOIN indexing_runs ir ON dp.last_indexed_run_id = ir.id
        WHERE ir.scope_json = ?
          AND dp.last_indexed_run_id != ?
        """,
        (scope_json, run_id),
    )
    
    stale_document_ids = [row["document_part_id"] for row in rows]
    stale_chunk_ids = [json.loads(row["chunk_ids"]) if row["chunk_ids"] else [] for row in rows]
    return stale_document_ids, stale_chunk_ids

def remove_document_parts_by_id(document_part_ids: List[str]) -> None:
    execute(
        f"""
        DELETE FROM document_parts
        WHERE document_part_id IN ({','.join('?' for _ in document_part_ids)})
        """,
        tuple(document_part_ids),
    )

def get_document_stats() -> dict:
    row = fetch_one(
        """
        SELECT
            COUNT(*) AS total_document_parts,
            COUNT(DISTINCT source_instance_id) AS total_sources,
            COUNT(DISTINCT device_id) AS total_devices
        FROM document_parts
        """,
    )
    if row:
        return dict(row)
    else:
        return {"total_document_parts": 0, "total_sources": 0, "total_devices": 0}

def get_document_stats_per_source() -> List[dict]:
    rows = fetch_all(
        """
        SELECT
            ms.id AS source_id,
            dp.source_type,
            dp.scope_json,
            COUNT(*) AS document_part_count
        FROM document_parts dp
        JOIN monitored_sources ms 
            ON ms.scope_json = dp.scope_json
            AND ms.source_type = dp.source_type
        GROUP BY ms.id, dp.source_type, dp.scope_json
        """,
    )
    return [dict(row) for row in rows]
