from pathlib import Path
import hashlib

from storage.metadata_db.db import init_db
from storage.metadata_db.indexing_runs import load_latest_run_by_scope, create_run
from src.domain.models import FilesystemIndexingScope
from api.app.services.ingestion import ingest_filesystem_scope
from collectors.filesystem import filesystem_source


def hash_content(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_ingestion_service_is_resumable(tmp_path):
    init_db()

    # Create fake filesystem content
    doc_path = tmp_path / "doc.md"
    content = "hello world"
    doc_path.write_text(content)
    
    filesystem_source.LOSEME_DATA_DIR = tmp_path
    filesystem_source.LOSEME_SOURCE_ROOT_HOST = tmp_path

    scope = FilesystemIndexingScope(type='filesystem',directories=[tmp_path])
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
    run = load_latest_run_by_scope(scope)
    assert run is not None

