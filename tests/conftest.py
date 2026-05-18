"""
Root conftest.py — shared fixtures for the entire test suite.

All tests run without GPU, Qdrant, or heavy ML models.
InMemoryVectorStore + DummyEmbeddingProvider are injected everywhere.
"""
import hashlib
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Paths & inline stubs so tests can run without the full server package on
# sys.path — pytest is expected to be invoked from the repo root with
#   PYTHONPATH=server:client:core pytest tests/
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# In-memory SQLite DB fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def db_conn() -> Generator[sqlite3.Connection, None, None]:
    """
    Provide a fresh in-memory SQLite connection with the full schema applied.
    Each test gets its own isolated database.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")

    # Minimal schema — mirrors production migrations
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY
        );

        CREATE TABLE IF NOT EXISTS vector_migrations (
            version TEXT PRIMARY KEY
        );

        CREATE TABLE IF NOT EXISTS indexing_runs (
            id TEXT PRIMARY KEY,
            celery_task_id TEXT NOT NULL DEFAULT '0',
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
            chunker_name TEXT,
            chunker_version TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_indexed_at TEXT,
            scope_json TEXT
        );

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

        CREATE TABLE IF NOT EXISTS monitored_sources (
            id TEXT NOT NULL PRIMARY KEY,
            source_type TEXT NOT NULL,
            locator TEXT NOT NULL,
            scope_json TEXT NOT NULL UNIQUE,
            last_seen_fingerprint TEXT,
            last_checked_at TIMESTAMP,
            last_ingested_at TIMESTAMP,
            enabled BOOLEAN DEFAULT 1,
            created_at TIMESTAMP NOT NULL,
            device_id TEXT
        );
    """)
    conn.commit()
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Dummy embedding provider
# ---------------------------------------------------------------------------

@pytest.fixture
def dummy_embedder():
    """Return the DummyEmbeddingProvider (CPU, deterministic)."""
    from pipeline.embeddings.dummy import DummyEmbeddingProvider
    return DummyEmbeddingProvider(dimension=384)


# ---------------------------------------------------------------------------
# In-memory vector store
# ---------------------------------------------------------------------------

@pytest.fixture
def memory_store():
    """Return a fresh InMemoryVectorStore."""
    from storage.vector_db.in_memory import InMemoryVectorStore
    return InMemoryVectorStore(dimension=384)


# ---------------------------------------------------------------------------
# Convenience: make a DocumentPart
# ---------------------------------------------------------------------------

def _make_part(
    text: str = "hello world",
    source_instance_id: str = "src-instance-1",
    unit_locator: str = "filesystem:/tmp/doc.txt",
    device_id: str = "device-1",
    source_path: str = "/tmp/doc.txt",
    extractor_name: str = "plaintext",
    extractor_version: str = "0.1",
    chunker_name: str = "simple",
    chunker_version: str = "1.0",
    source_type: str = "filesystem",
):
    from loseme_core.ids import make_logical_document_part_id
    from loseme_core.document_models import DocumentPart

    checksum = hashlib.sha256(text.encode()).hexdigest()
    doc_part_id = make_logical_document_part_id(source_instance_id, unit_locator)

    return DocumentPart(
        text=text,
        document_part_id=doc_part_id,
        checksum=checksum,
        source_type=source_type,
        source_instance_id=source_instance_id,
        device_id=device_id,
        source_path=source_path,
        unit_locator=unit_locator,
        content_type="text/plain",
        extractor_name=extractor_name,
        extractor_version=extractor_version,
        scope_json={"type": source_type, "directories": ["/tmp"]},
    )


@pytest.fixture
def make_part():
    """Fixture exposing the _make_part factory."""
    return _make_part
