import sqlite3
from pathlib import Path
from typing import Iterator

DB_PATH = Path(__file__).parent / "indexing.db"


def get_connection() -> sqlite3.Connection:
    """
    Returns a SQLite connection and ensures foreign keys are enabled.
    """
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
                source_type TEXT NOT NULL,
                scope_json TEXT NOT NULL,
                status TEXT NOT NULL,
                last_document_id TEXT,
                started_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_documents (
                run_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                content_hash TEXT,
                PRIMARY KEY (run_id, document_id),
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
    from src.core.logging import logger

    tables = fetch_all("SELECT name, sql FROM sqlite_master WHERE type='table'")
    indexes = fetch_all("SELECT name, sql FROM sqlite_master WHERE type='index'")

    logger.info("=== Active DB schema ===")
    for t in tables:
        logger.info("TABLE %s: %s", t["name"], t["sql"])
    for i in indexes:
        logger.info("INDEX %s: %s", i["name"], i["sql"])

