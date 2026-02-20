import os
import hashlib
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
from api.app.tasks.celery_app import celery_app
celery_app.conf.task_always_eager = True
from api.app.tasks.ingestion_tasks import ingest_run_task

from fastapi.testclient import TestClient

from api.app.main import app
from src.sources.base.models import Document
from src.sources.filesystem.filesystem_model import FilesystemIndexingScope
from src.core.ids import make_logical_document_part_id, make_source_instance_id
from storage.metadata_db.indexing_runs import create_run, load_latest_run_by_scope
#from collectors.filesystem import filesystem_source
from src.sources.filesystem import filesystem_source
from unittest.mock import MagicMock, patch
import pytest

import logging
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Test setup: enforce Docker-like ingestion root
# ------------------------------------------------------------------

DATA_ROOT = Path("/tmp/loseme_test_data").resolve()
os.environ["LOSEME_DATA_DIR"] = str(DATA_ROOT)
DATA_ROOT.mkdir(parents=True, exist_ok=True)

client = TestClient(app)

filesystem_source.LOSEME_DATA_DIR = DATA_ROOT
filesystem_source.LOSEME_SOURCE_ROOT_HOST = DATA_ROOT

# -------------------------------------------------------------------
# Tests
# -------------------------------------------------------------------

@pytest.fixture()
def mock_vector_store():
    with patch("storage.vector_db.runtime.get_vector_store") as mock_store:
        mock_instance = MagicMock()
        mock_store.return_value = mock_instance
        yield mock_instance


def test_ingest_filesystem_success(setup_db, mock_vector_store):
    ingest_dir = DATA_ROOT / "docs"
    ingest_dir.mkdir(exist_ok=True)

    file1 = ingest_dir / "file1.txt"
    file2 = ingest_dir / "file2.txt"

    file1_content = "Content of file 1"
    file2_content = "Content of file 2"
    
    file1.write_text(file1_content)
    file2.write_text(file2_content)
    

    
    # Create a run for the test
    scope = FilesystemIndexingScope(type="filesystem", directories=[str(ingest_dir)])
    create_run("filesystem", scope)
    run = load_latest_run_by_scope(scope)
    run_id = run.id
   
    logger.debug(f"Created run with ID: {run_id} for scope: {scope}")
    response = client.post(
            "/ingest/document_part",
            json={
                "run_id": run_id,
                "document_part_id": make_logical_document_part_id(file1_content, unit_locator=f"filesystem:{file1}"),
                "source_type": "filesystem",
                "checksum": hashlib.sha256(
                    file1_content.encode("utf-8")
                ).hexdigest(),
                "device_id": "device123",
                "source_path": str(file1),
                "source_instance_id": make_source_instance_id("filesystem", "device123", Path("/docs")),
                "unit_locator": f"filesystem:{file1}",
                "content_type": "text/plain",
                "extractor_name": "simple_text_extractor",
                "extractor_version": "1.0.0",
                "metadata_json": {"author": "Test Author"},
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "text": file1_content,
                "scope_json": scope.serialize(),
            },
        )

    logger.debug(f"Ingest response for file1: {response.json()}")
    
    assert response.status_code == 200

    data = response.json()
    assert data["accepted"] is True

if __name__ == "__main__":
    test_ingest_filesystem_success(None)
