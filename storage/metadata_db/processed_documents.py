from storage.metadata_db.db import execute, fetch_all, fetch_one

def add_discovered_document(run_id: str, source_instance_id: str, content_checksum: str):
    execute(
        """
        INSERT OR IGNORE INTO processed_documents
        (run_id, source_instance_id, content_hash, is_indexed)
        VALUES (?, ?, ?, ?)
        """,
        (run_id, source_instance_id, content_checksum, 0),
    )


def mark_processed(run_id: str, source_instance_id: str, content_checksum: str):
    execute(
        """
        INSERT INTO processed_documents
        (run_id, source_instance_id, content_hash, is_indexed)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(run_id, source_instance_id, content_hash) DO UPDATE SET
            is_indexed = excluded.is_indexed
        """,
        (run_id, source_instance_id, content_checksum, 1),
    )

def unmark_processed(run_id: str, source_instance_id: str, content_checksum: str):
    execute(
        """
        UPDATE processed_documents
        SET is_indexed = 0
        WHERE run_id = ?
          AND source_instance_id = ?
          AND content_hash = ?
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
        SELECT 1
        FROM processed_documents
        WHERE source_instance_id = ?
          AND content_hash = ?
          AND is_indexed = 1
        LIMIT 1
        """,
        (source_instance_id, content_checksum),
    )
    return row is not None

def get_all_processed(run_id: str) -> set[str]:
    """
    Return all processed document IDs for a run.
    Useful for resume logic and debugging.
    """
    rows = fetch_all(
        """
        SELECT source_instance_id || ':' || content_hash AS document_key
        FROM processed_documents
        WHERE run_id = ?
          AND is_indexed = 1
        """,
        (run_id,),
    )
    return {row["document_key"] for row in rows}
