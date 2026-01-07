from storage.metadata_db.db import execute, fetch_all, fetch_one


def mark_processed(run_id: str, document_id: str, content_hash: str):
    execute(
        """
        INSERT OR REPLACE INTO processed_documents
        (run_id, document_id, content_hash)
        VALUES (?, ?, ?)
        """,
        (run_id, document_id, content_hash)
    )

def is_processed(run_id: str, document_id: str, content_hash: str) -> bool:
    row = fetch_one(
        """
        SELECT content_hash FROM processed_documents
        WHERE run_id = ? AND document_id = ?
        """,
        (run_id, document_id),
    )
    return row is not None and row["content_hash"] == content_hash


def get_all_processed(run_id: str) -> set[str]:
    """
    Return all processed document IDs for a run.
    Useful for resume logic and debugging.
    """
    rows = fetch_all(
        """
        SELECT document_id
        FROM processed_documents
        WHERE run_id = ?
        """,
        (run_id,),
    )
    return {row["document_id"] for row in rows}

