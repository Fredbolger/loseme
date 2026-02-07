import json
from datetime import datetime
from typing import Optional, Tuple
from storage.metadata_db.db import execute, fetch_one
from src.sources.base.models import Document, IndexingScope, IngestionSource
from src.sources.base.registry import indexing_scope_registry

def upsert_document(doc: dict, run_id: Optional[str] = None) -> None:
    execute(
        """
        INSERT INTO documents (
            document_id,
            logical_checksum,
            source_type,
            source_instance_id,
            device_id,
            source_path,
            metadata_json,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(document_id) DO UPDATE SET
            source_path = excluded.source_path,
            metadata_json = excluded.metadata_json,
            updated_at = excluded.updated_at
        """,
        (
            doc["id"],
            doc["checksum"],
            doc["source_type"],
            doc["source_id"],
            doc["device_id"],
            doc["source_path"],
            json.dumps(doc.get("metadata", {})),
            doc["created_at"].isoformat(),
            doc["updated_at"].isoformat(),
        ),
    )

def get_document_by_id(document_id: str) -> Optional[dict]:
    row = fetch_one(
        "SELECT * FROM documents WHERE document_id = ?",
        (document_id,),
    )
    return dict(row) if row else None

def retrieve_source(document_id: str) -> Optional[Tuple[str, IndexingScope]]:
    """
    Retrieve the source type and indexing scope that produced a document.

    Uses the most recent indexing run that processed the document's
    source_instance_id + logical_checksum.
    """
    row = fetch_one(
        """
        SELECT
            r.source_type AS source_type,
            r.scope_json AS scope_json
        FROM documents d
        JOIN processed_documents p
          ON p.source_instance_id = d.source_instance_id
         AND p.content_hash = d.logical_checksum
        JOIN indexing_runs r
          ON r.id = p.run_id
        WHERE d.document_id = ?
        ORDER BY r.started_at DESC
        LIMIT 1
        """,
        (document_id,),
    )

    if row is None:
        return None

    scope = indexing_scope_registry.deserialize(json.loads(row["scope_json"]))
    return row["source_type"], scope

def get_update_timestamp(document_id: str) -> Optional[datetime]:
    # fetch the updated_at timestamp for a document by
    # first retrieving the associated run_id from the processed_documents table
    run_id = fetch_one(
        """
        SELECT run_id FROM processed_documents p
        JOIN documents d ON p.source_instance_id = d.source_instance_id
                      AND p.content_hash = d.logical_checksum
        WHERE d.document_id = ?
        ORDER BY p.run_id DESC
        LIMIT 1
        """,
        (document_id,),
    )
    
    if run_id is None:
        return None

    # then fetch the updated_at timestamp from the indexing_runs table
    updated_at = fetch_one(
        "SELECT updated_at FROM indexing_runs WHERE id = ?",
        (run_id["run_id"],),
    )
    run_status = fetch_one(
        "SELECT status FROM indexing_runs WHERE id = ?",
        (run_id["run_id"],),
    )

    # only return if the run was marked as completed, otherwise return None
    if run_status and run_status["status"] == "completed": 
        return datetime.fromisoformat(updated_at["updated_at"]) if updated_at else None
    else:
        return None
