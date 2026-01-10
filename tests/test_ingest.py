import os
import hashlib
from pathlib import Path
from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.app.main import app
from src.domain.models import Document
from src.domain.ids import make_logical_document_id, make_source_instance_id

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

    file1 = ingest_dir / "file1.txt"
    file2 = ingest_dir / "file2.txt"

    file1.write_text("Content of file 1")
    file2.write_text("Content of file 2")

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
    assert data["documents_ingested"] == 2

"""
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
"""
