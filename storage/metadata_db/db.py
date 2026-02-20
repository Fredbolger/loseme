import sqlite3
import os
from pathlib import Path
from typing import Iterator
from storage.metadata_db.migrations import run_migrations

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
                stop_requested INTEGER NOT NULL DEFAULT 0,
                is_discovering INTEGER NOT NULL DEFAULT 1,
                is_indexing INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS document_parts (
            document_part_id TEXT PRIMARY KEY,
            checksum TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_instance_id TEXT NOT NULL,
            device_id TEXT NOT NULL,
            source_path TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            last_indexed_run_id TEXT,
            chunk_ids TEXT,
            unit_locator TEXT,
            content_type TEXT,
            extractor_name TEXT,
            extractor_version TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_indexed_at TEXT,
            scope_json TEXT
            );
            """
        )
        conn.execute(
             """
            CREATE TABLE IF NOT EXISTS document_parts_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            document_part_id TEXT NOT NULL,
            checksum TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_instance_id TEXT NOT NULL,
            device_id TEXT NOT NULL,
            source_path TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            unit_locator TEXT,
            content_type TEXT,
            extractor_name TEXT,
            extractor_version TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            text TEXT,
            scope_json TEXT
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS monitored_sources (
            id TEXT NOT NULL PRIMARY KEY,                      -- stable source instance id
            source_type TEXT NOT NULL,             -- e.g. 'thunderbird', 'filesystem'
            locator TEXT NOT NULL,                 -- path, glob, or logical identifier
            scope_json TEXT NOT NULL UNIQUE,  -- serialized IndexingScope
            last_seen_fingerprint TEXT,            -- hash / mtime / size summary
            last_checked_at TIMESTAMP,
            last_ingested_at TIMESTAMP,
            enabled BOOLEAN DEFAULT 1,
            created_at TIMESTAMP NOT NULL
            );
            """
        )
        run_migrations(conn)  # <-- run migrations after ensuring base tables exist

        
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


def get_document_part(document_part_id: str) -> sqlite3.Row:
    """
    Retrieves a document part by its ID.
    """
    query = "SELECT * FROM document_parts WHERE document_part_id = ?"
    with get_connection() as conn:
        cur = conn.execute(query, (document_part_id,))
        return cur.fetchone()

def delete_database() -> None:
    """
    Deletes the database file. Use with caution.
    """
    if DB_PATH.exists():
        DB_PATH.unlink()
