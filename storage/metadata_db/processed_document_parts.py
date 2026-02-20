from storage.metadata_db.db import execute, fetch_all, fetch_one
import json

def add_discovered_document_part(run_id: str, source_instance_id: str, content_checksum: str, unit_locator: str, content_type: str, extractor_name: str, extractor_version: str):
    execute(
        """
        INSERT OR IGNORE INTO processed_document_parts
        (run_id, chunk_ids, source_instance_id, content_hash, is_indexed, unit_locator, content_type, extractor_name, extractor_version)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (run_id, "[]" , source_instance_id, content_checksum, 0, unit_locator, content_type, extractor_name, extractor_version),
    )


def mark_part_processed(run_id: str, chunk_ids: list[str], source_instance_id: str, content_checksum: str, unit_locator: str, content_type: str, extractor_name: str, extractor_version: str):
    execute(
        """
        INSERT INTO processed_document_parts
        (run_id, chunk_ids, source_instance_id, content_hash, is_indexed, unit_locator, content_type, extractor_name, extractor_version)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_id, source_instance_id, content_hash) DO UPDATE SET
            is_indexed = excluded.is_indexed
        """,
        (run_id, json.dumps(chunk_ids), source_instance_id, content_checksum, 1, unit_locator, content_type, extractor_name, extractor_version),
    )

def unmark_part_processed(run_id: str, source_instance_id: str, content_checksum: str):
    execute(
        """
        UPDATE processed_document_parts
        SET is_indexed = 0
        WHERE run_id = ?
          AND source_instance_id = ?
          AND content_hash = ?
        """,
        (run_id, source_instance_id, content_checksum),
    )

def part_is_processed(source_instance_id: str, unit_locator: str) -> tuple[bool, dict]:
    """
    Returns (True, {"extractor_name": ..., "extractor_version": ...}) if the document part
    has ever been processed (regardless of run).
    """
    row = fetch_one(
        """
        SELECT is_indexed, extractor_name, extractor_version
        FROM processed_document_parts
        WHERE source_instance_id = ?
          AND unit_locator = ?
        """,
        (source_instance_id, unit_locator)
    )
    if row:
        return bool(row["is_indexed"]), {"extractor_name": row["extractor_name"], "extractor_version": row["extractor_version"]}
    else:
        return False, {}


def get_all_processed_parts(source_instance_id: str) -> list[dict]:
    """
    Returns a list of all processed parts for a given source_instance_id, regardless of run.
    """
    rows = fetch_all(
        """
        SELECT content_hash, unit_locator, content_type, extractor_name, extractor_version
        FROM processed_document_parts
        WHERE source_instance_id = ?
          AND is_indexed = 1
        """,
        (source_instance_id,),
    )
    return [{"content_hash": row["content_hash"], "unit_locator": row["unit_locator"], "content_type": row["content_type"], "extractor_name": row["extractor_name"], "extractor_version": row["extractor_version"]} for row in rows]

def get_all_processed_party_by_run_id(run_id: str) -> list[dict]:
    """
    Returns a list of all processed parts for a given run_id.
    """
    rows = fetch_all(
        """
        SELECT content_hash, unit_locator, content_type, extractor_name, extractor_version
        FROM processed_document_parts
        WHERE run_id = ?
          AND is_indexed = 1
        """,
        (run_id,),
    )
    return [{"content_hash": row["content_hash"], "unit_locator": row["unit_locator"], "content_type": row["content_type"], "extractor_name": row["extractor_name"], "extractor_version": row["extractor_version"]} for row in rows]

def get_stale_parts(run_id: str, source_instance_id: str):
    return fetch_all(
        """
        SELECT document_part_id, chunk_ids
        FROM document_parts
        WHERE source_instance_id = ?
          AND last_indexed_run_id != ?
        """,
        (source_instance_id, run_id),
    )

def get_all_parts(source_instance_id: str) -> list[dict]:
    rows = fetch_all(
        """
        SELECT is_indexed, chunk_ids, unit_locator, content_type, extractor_name, extractor_version
        FROM processed_document_parts
        WHERE source_instance_id = ?
        """,
        (source_instance_id,),
    )
    return [dict(row) for row in rows]
