import sqlite3
from pathlib import Path
from typing import Iterator

DB_PATH = Path("/var/lib/loseme/metadata/metadata.db")

def get_connection() -> sqlite3.Connection:
    """
    Returns a SQLite connection and ensures foreign keys are enabled.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)  # <-- ensure directory exists
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """
    Initializes required tables if they do not exist.
    Safe to call multiple times.
    """
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS indexing_runs (
                id TEXT PRIMARY KEY,
                celery_task_id TEXT NOT NULL,
                source_type TEXT NOT NULL,
                scope_json TEXT NOT NULL,
                status TEXT NOT NULL,
                last_document_id TEXT,
                started_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                discovered_document_count INTEGER NOT NULL DEFAULT 0,
                indexed_document_count INTEGER NOT NULL DEFAULT 0,
                stop_requested INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
            document_id TEXT PRIMARY KEY,
            logical_checksum TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_instance_id TEXT NOT NULL,
            device_id TEXT NOT NULL,
            source_path TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_documents (
            run_id TEXT NOT NULL,
            source_instance_id TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            PRIMARY KEY (run_id, source_instance_id, content_hash),
            FOREIGN KEY (run_id) REFERENCES indexing_runs(id)
                ON DELETE CASCADE
            );
            """
        )


def execute(query: str, params: tuple = ()) -> None:
    """
    Executes a query with the provided parameters.
    """
    with get_connection() as conn:
        conn.execute(query, params)
        conn.commit()


def fetch_one(query: str, params: tuple = ()):
    """
    Fetches a single row from the database for the given query and parameters.
    """
    with get_connection() as conn:
        cur = conn.execute(query, params)
        return cur.fetchone()


def fetch_all(query: str, params: tuple = ()) -> list:
    """
    Fetches all rows from the database for the given query and parameters.
    """
    with get_connection() as conn:
        cur = conn.execute(query, params)
        return cur.fetchall()


def log_active_schema() -> None:
    """
    Logs current database schema using the project logger.
    """
    # Lazy import to prevent import-time failures
    import logging
    logger = logging.getLogger(__name__)

    tables = fetch_all("SELECT name, sql FROM sqlite_master WHERE type='table'")
    indexes = fetch_all("SELECT name, sql FROM sqlite_master WHERE type='index'")

    logger.info("=== Active DB schema ===")
    for t in tables:
        logger.info("TABLE %s: %s", t["name"], t["sql"])
    for i in indexes:
        logger.info("INDEX %s: %s", i["name"], i["sql"])

def get_document(document_id: str) -> Iterator[sqlite3.Row]:
    """
    Retrieves a document by its ID.
    """
    query = "SELECT * FROM documents WHERE id = ?"
    with get_connection() as conn:
        cur = conn.execute(query, (document_id,))
        for row in cur:
            yield row

def delete_database() -> None:
    """
    Deletes the database file. Use with caution.
    """
    if DB_PATH.exists():
        DB_PATH.unlink()
