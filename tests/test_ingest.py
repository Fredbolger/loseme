import os
import hashlib
from pathlib import Path
from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.app.main import app
from src.domain.models import Document
from src.domain.ids import make_logical_document_id, make_source_instance_id
from collectors.filesystem import filesystem_source

# -------------------------------------------------------------------
# Test setup: enforce Docker-like ingestion root
# -------------------------------------------------------------------

DATA_ROOT = Path("/tmp/loseme_test_data").resolve()
os.environ["LOSEME_DATA_DIR"] = str(DATA_ROOT)
DATA_ROOT.mkdir(parents=True, exist_ok=True)

client = TestClient(app)

filesystem_source.LOSEME_DATA_DIR = DATA_ROOT
filesystem_source.LOSEME_SOURCE_ROOT_HOST = DATA_ROOT

# -------------------------------------------------------------------
# Tests
# -------------------------------------------------------------------


def test_ingest_filesystem_success(setup_db):
    print("IN DOCKER:", Path("/.dockerenv").exists())

    ingest_dir = DATA_ROOT / "docs"
    ingest_dir.mkdir(exist_ok=True)

    file1 = ingest_dir / "file1.txt"
    file2 = ingest_dir / "file2.txt"

    file1.write_text("Content of file 1")
    file2.write_text("Content of file 2")

    response = client.post(
        "/ingest/filesystem",
        json={
            "directories": [str(ingest_dir)],
            "recursive": True,
            "include_patterns": [],
            "exclude_patterns": [],
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "running"

if __name__ == "__main__":
    test_ingest_filesystem_success()
    print("Test passed.")
