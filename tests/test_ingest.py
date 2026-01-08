import os
from pathlib import Path
from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.app.main import app
from src.domain.models import Document

# -------------------------------------------------------------------
# Test setup: enforce Docker-like ingestion root
# -------------------------------------------------------------------

DATA_ROOT = Path("/tmp/loseme_test_data").resolve()
os.environ["LOSEME_DATA_DIR"] = str(DATA_ROOT)
DATA_ROOT.mkdir(parents=True, exist_ok=True)

client = TestClient(app)

# -------------------------------------------------------------------
# Tests
# -------------------------------------------------------------------

def test_ingest_filesystem_success():
    ingest_dir = DATA_ROOT / "docs"
    ingest_dir.mkdir(exist_ok=True)

    fake_docs = [
        Document(
            id="1",
            source=str(ingest_dir / "file1.txt"),
            metadata={},
            checksum="abc123",
            created_at=datetime.utcnow(),
            content="Content of file 1",
        ),
        Document(
            id="2",
            source=str(ingest_dir / "file2.txt"),
            metadata={},
            checksum="def456",
            created_at=datetime.utcnow(),
            content="Content of file 2",
        ),
    ]

    with patch(
        "src.domain.ingestion.FilesystemIngestionSource.list_documents",
        return_value=fake_docs,
    ):
        response = client.post(
            "/ingest/filesystem",
            json={
                "path": str(ingest_dir),
                "recursive": True,
                "include_patterns": [],
                "exclude_patterns": [],
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["documents_ingested"] == len(fake_docs)

def test_ingest_filesystem_invalid_path():
    response = client.post(
        "/ingest/filesystem",
        json={"path": "/does/not/exist"},
    )

    assert response.status_code == 400

def test_ingest_filesystem_no_documents():
    empty_dir = DATA_ROOT / "empty"
    empty_dir.mkdir(exist_ok=True)

    with patch(
        "src.domain.ingestion.FilesystemIngestionSource.list_documents",
        return_value=[],
    ):
        response = client.post(
            "/ingest/filesystem",
            json={
                "path": str(empty_dir),
                "recursive": True,
                "include_patterns": [],
                "exclude_patterns": [],
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["documents_ingested"] == 0

