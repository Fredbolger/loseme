import json
from typing import Optional
from storage.metadata_db.db import execute, fetch_one, fetch_all
import logging

logger = logging.getLogger(__name__)

def add_document_part_to_queue(
    part: dict,
    run_id: str,
) -> None:
    """
    Add a document part to the processing queue.
    This is used for parts that need to be processed asynchronously, such as extracting text from a PDF.
    """
    execute(
        """
        INSERT INTO document_parts_queue (
            run_id,
            document_part_id,
            checksum,
            source_type,
            source_instance_id,
            device_id,
            source_path,
            metadata_json,
            unit_locator,
            content_type,
            extractor_name,
            extractor_version,
            created_at,
            updated_at,
            text,
            scope_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            part["document_part_id"],
            part["checksum"],
            part["source_type"],
            part["source_instance_id"],
            part["device_id"],
            part["source_path"],
            json.dumps(part.get("metadata", {})),
            part["unit_locator"],
            part["content_type"],
            part["extractor_name"],
            part["extractor_version"],
            part["created_at"].isoformat(),
            part["updated_at"].isoformat(),
            part["text"],
            json.dumps(part.get("scope_json"))
            ),
    )

def get_next_document_part_from_queue(run_id: str) -> Optional[dict]:
    """
    Get the next document part from the processing queue for a given run_id.
    This is used by the worker process to get the next part that needs to be processed.
    """
    
    row = fetch_one(
        """
        SELECT *
        FROM document_parts_queue
        WHERE run_id = ?
        ORDER BY created_at ASC
        LIMIT 1
        """,
        (run_id,)
    )

    if row is None:
        return None
    else: 
        part = dict(row)
        part["metadata_json"] = json.loads(part["metadata_json"])
        return part

def remove_document_part_from_queue(run_id: str, document_part_id: str) -> None:
    """
    Remove a document part from the processing queue after it has been processed.
    This is used by the worker process to remove the part from the queue once it has been processed.
    """
    execute(
        """
        DELETE FROM document_parts_queue
        WHERE run_id = ? AND document_part_id = ?
        """,
        (run_id, document_part_id)
    )
    
def get_all_document_parts_in_queue_for_run(run_id: str) -> list:
    """
    Get all document parts currently in the queue for a given run_id.
    This is used for debugging and monitoring purposes to see what parts are still in the queue.
    """
    logger.debug(f"Fetching all document parts in queue for run_id {run_id}")
    rows = fetch_all(
        """
        SELECT *
        FROM document_parts_queue
        WHERE run_id = ?
        """,
        (run_id,)
    )

    parts = []
    if not rows:
        return parts

    for row in rows:
        part = dict(row)
        parts.append(part)
        
    return parts

def get_all_document_parts_in_queue() -> list:
    """
    Get all document parts currently in the queue for a given run_id.
    This is used for debugging and monitoring purposes to see what parts are still in the queue.
    """
    rows = fetch_all(
        """
        SELECT *
        FROM document_parts_queue
        """
    )

    parts = []
    if not rows:
        return parts

    for row in rows:
        part = dict(row)
        part["metadata_json"] = json.loads(part["metadata_json"])
        parts.append(part)
        
    return parts

def clear_queue_for_run(run_id: str) -> None:
    """
    Clear all document parts from the queue for a given run_id.
    This is used for debugging and monitoring purposes to clear the queue if needed.
    """
    execute(
        """
        DELETE FROM document_parts_queue
        WHERE run_id = ?
        """,
        (run_id,)
    )

def clear_all_queues() -> None:
    """
    Clear all document parts from the queue across all run_ids.
    This is used for debugging and monitoring purposes to clear all queues if needed.
    """
    execute(
        """
        DELETE FROM document_parts_queue
        """
    )
