import os
import hashlib
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
from api.app.tasks.celery_app import celery_app
celery_app.conf.task_always_eager = True
from api.app.tasks.ingestion_tasks import ingest_document_task

assert ingest_document_task.app.conf.task_always_eager is True

from fastapi.testclient import TestClient

from api.app.main import app
from src.domain.models import Document
from src.domain.ids import make_logical_document_id, make_source_instance_id
from collectors.filesystem import filesystem_source
from api.app.schemas.ingest_documents import IngestDocumentsRequest, IngestedChunk, IngestedDocument
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

    file1.write_text("Content of file 1")
    file2.write_text("Content of file 2")
    
    file1_content = "Content of file 1"
    file2_content = "Content of file 2"

    response = client.post(
        "/ingest/documents",
        json={
            "documents": [
                {
                    "id": make_logical_document_id(file1_content),
                    "source_type": "filesystem",
                    "source_id": make_source_instance_id("filesystem", "device123", Path("/docs")),
                    "device_id": "device123",
                    "source_path": str(file1),
                    "checksum": hashlib.sha256(
                        "Content of file 1".encode("utf-8")
                    ).hexdigest(),
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "metadata": {
                        "author": "Test Author",
                    },
                    "chunks": [
                        {
                            "id": f"{make_logical_document_id(file1_content)}_chunk_0",
                            "document_id": make_logical_document_id(file1_content),
                            "source_type": "filesystem",
                            "device_id": "device123",
                            "index": 0,
                            "text": file1_content,
                            "metadata": {"page": 1},
                        }
                    ],
                }
            ]
        },
    )


    logger.debug(f"Ingest response for file1: {response.json()}")
    
    assert response.status_code == 200

    data = response.json()
    assert data["accepted"] is True

if __name__ == "__main__":
    test_ingest_filesystem_success(None)
