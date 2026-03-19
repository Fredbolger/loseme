"""
Shared helpers and fixtures for the release-critical test suite.

Import this module in each test file:
    from tests.helpers import make_part, ingest_part, create_filesystem_run
"""

import hashlib

import pytest
from fastapi.testclient import TestClient

from api.app.main import app
from api.app.tasks.celery_app import celery_app
from src.core.ids import make_logical_document_part_id
from src.sources.base.models import DocumentPart
from src.sources.filesystem.filesystem_model import FilesystemIndexingScope
from storage.metadata_db.indexing_runs import create_run, load_latest_run_by_scope

# Run Celery tasks synchronously — no broker needed in tests.
celery_app.conf.task_always_eager = True

client = TestClient(app)


# ---------------------------------------------------------------------------
# Document-part factory
# ---------------------------------------------------------------------------

def make_part(
    text: str = "hello world",
    source_instance_id: str = "src-instance-1",
    unit_locator: str = "filesystem:/tmp/doc.txt",
    device_id: str = "device-1",
    source_path: str = "/tmp/doc.txt",
) -> DocumentPart:
    """Return a minimal, fully-populated DocumentPart suitable for ingestion."""
    checksum = hashlib.sha256(text.encode()).hexdigest()
    doc_part_id = make_logical_document_part_id(source_instance_id, unit_locator)
    return DocumentPart(
        text=text,
        document_part_id=doc_part_id,
        checksum=checksum,
        source_type="filesystem",
        source_instance_id=source_instance_id,
        device_id=device_id,
        source_path=source_path,
        unit_locator=unit_locator,
        content_type="text/plain",
        extractor_name="txt_extractor",
        chunker_name="simple",
        chunker_version="1.0",
        extractor_version="1.0",
    )


# ---------------------------------------------------------------------------
# Ingest helper
# ---------------------------------------------------------------------------

def ingest_part(part: DocumentPart, run_id: str) -> dict:
    """POST a document part to /ingest/document_part and return the JSON body."""
    resp = client.post(
        "/ingest/document_part",
        json={
            "run_id": run_id,
            "document_part_id": part.document_part_id,
            "checksum": part.checksum,
            "source_type": part.source_type,
            "source_instance_id": part.source_instance_id,
            "device_id": part.device_id,
            "source_path": part.source_path,
            "unit_locator": part.unit_locator,
            "content_type": part.content_type,
            "extractor_name": part.extractor_name,
            "extractor_version": part.extractor_version,
            "metadata_json": part.metadata_json,
            "created_at": part.created_at.isoformat(),
            "updated_at": part.updated_at.isoformat(),
            "text": part.text,
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Run factory
# ---------------------------------------------------------------------------

def create_filesystem_run(path: str = "/tmp/docs") -> str:
    """Create a filesystem indexing run and return its run_id."""
    scope = FilesystemIndexingScope(type="filesystem", directories=[path])
    create_run("filesystem", scope)
    run = load_latest_run_by_scope(scope)
    return run.id
