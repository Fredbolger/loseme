from storage.metadata_db.db import execute, fetch_all, fetch_one

def mark_processed(run_id: str, source_instance_id: str, content_checksum: str):
    execute(
        """
        INSERT OR IGNORE INTO processed_documents
        (run_id, source_instance_id, content_hash)
        VALUES (?, ?, ?)
        """,
        (run_id, source_instance_id, content_checksum),
    )

def unmark_processed(run_id: str, source_instance_id: str, content_checksum: str):
    execute(
        """
        DELETE FROM processed_documents
        WHERE run_id = ? AND source_instance_id = ? AND content_hash = ?
        """,
        (run_id, source_instance_id, content_checksum),
    )

def is_processed(source_instance_id: str, content_checksum: str) -> bool:
    """
    Returns True if a document with this checksum and source_instance_id
    has ever been processed (regardless of run).
    """
    row = fetch_one(
        """
        SELECT content_hash
        FROM processed_documents
        WHERE source_instance_id = ?
          AND content_hash = ?
        """,
        (source_instance_id, content_checksum),
    )
    return row is not None and row["content_hash"] == content_checksum


def get_all_processed(run_id: str) -> set[str]:
    """
    Return all processed document IDs for a run.
    Useful for resume logic and debugging.
    """
    rows = fetch_all(
        """
        SELECT source_instance_id
        FROM processed_documents
        WHERE run_id = ?
        """,
        (run_id,),
    )
    return {row["source_instance_id"] for row in rows}


