from pathlib import Path
import hashlib

from storage.metadata_db.db import init_db
from storage.metadata_db.indexing_runs import load_latest_run, create_run
from src.domain.models import IndexingScope
from api.app.services.ingestion import ingest_filesystem_scope


def hash_content(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_ingestion_service_is_resumable(tmp_path):
    init_db()

    # Create fake filesystem content
    doc_path = tmp_path / "doc.md"
    content = "hello world"
    doc_path.write_text(content)

    scope = IndexingScope(directories=[tmp_path])
    run = create_run("filesystem", scope)

    # First ingestion
    result1 = ingest_filesystem_scope(scope, run.id, resume=False)
    
    assert result1.documents_discovered == 1
    assert result1.documents_indexed == 1

    # Second ingestion (resume)
    result2 = ingest_filesystem_scope(scope, run.id, resume=True)

    assert result2.documents_discovered == 1
    assert result2.documents_indexed == 0

    # Ensure run continuity
    run = load_latest_run("filesystem", scope)
    assert run is not None

