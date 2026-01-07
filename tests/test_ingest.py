from fastapi.testclient import TestClient
from api.app.main import app
from unittest.mock import patch
from src.domain.ingestion import Document
from datetime import datetime
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

client = TestClient(app)

def test_ingest_filesystem_success():
    # Prepare fake documents
    fake_docs = [Document(id="1", source="/home/user/file1.txt", metadata={}, checksum="abc123", created_at=datetime.utcnow(), content="Content of file 1"),
                 Document(id="2", source="/home/user/IgnorePath/file2.txt", metadata={}, checksum="def456", created_at=datetime.utcnow(), content="Content of file 2")]

    with patch("src.domain.ingestion.FilesystemIngestionSource.list_documents", return_value=fake_docs):
        response = client.post("/ingest/filesystem", json={"path": "/tmp", "recursive": True, "include_patterns": [], "exclude_patterns": []})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["documents_ingested"] == len(fake_docs)

def test_ingest_filesystem_invalid_path():
    response = client.post("/ingest/filesystem", json={"path": "/does/not/exist"})
    assert response.status_code == 400
    assert "Path does not exist" in response.json()["detail"]

def test_ingest_filesystem_no_documents():
    with patch("src.domain.ingestion.FilesystemIngestionSource.list_documents", return_value=[]):
        response = client.post("/ingest/filesystem", json={"path": "/tmp", "recursive": True, "include_patterns": [], "exclude_patterns": []})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["documents_ingested"] == 0

