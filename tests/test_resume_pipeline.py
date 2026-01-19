from pathlib import Path
import pytest

from storage.metadata_db.db import init_db
from storage.metadata_db.processed_documents import is_processed, mark_processed, get_all_processed
from storage.metadata_db.indexing_runs import load_latest_run, create_run, update_status
from src.domain.models import IndexingScope
from api.app.services.ingestion import ingest_filesystem_scope, IngestionCancelled
from src.domain.ids import make_source_instance_id

from collectors.filesystem import filesystem_source

def test_resume_does_not_reindex_processed_documents(tmp_path):
    init_db()

    # Arrange
    doc_path = tmp_path / "doc.md"
    doc_path.write_text("hello world")
        
    filesystem_source.LOSEME_DATA_DIR = tmp_path
    filesystem_source.LOSEME_SOURCE_ROOT_HOST = tmp_path

    scope = IndexingScope(directories=[tmp_path])


    # API creates the run
    run = create_run("filesystem", scope)

    # Simulate partial ingestion (worker crash after first doc)
    ingest_filesystem_scope(scope, run.id, stop_after=1)
    
    # Explicitly mark as interrupted (this is what we're testing)
    update_status(run.id, "interrupted")

    # Sanity: run is NOT completed
    resumed = load_latest_run("filesystem", scope)
    assert resumed is not None
    assert resumed.id == run.id

    # Act: resume same run
    ingest_filesystem_scope(scope, run.id)

    # Assert: still only one processed document
    processed = get_all_processed(run.id)
    assert len(processed) == 1

def test_resume_reindexes_on_content_change(tmp_path):
    init_db()

    doc_path = tmp_path / "doc.md"
    doc_path.write_text("v1")
    
    filesystem_source.LOSEME_DATA_DIR = tmp_path
    filesystem_source.LOSEME_SOURCE_ROOT_HOST = tmp_path

    scope = IndexingScope(directories=[tmp_path])
    run = create_run("filesystem", scope)

    ingest_filesystem_scope(scope, run.id, resume=False)

    # Change content
    doc_path.write_text("v2")

    result = ingest_filesystem_scope(scope, run.id, resume=True)
    assert result.documents_indexed == 1

def test_resume_processes_unprocessed_documents(tmp_path):
    """
    Resume semantics:
    - Same run
    - Existing processed documents are skipped
    - Newly added documents ARE indexed
    """

    init_db()

    scope = IndexingScope(directories=[tmp_path])
    run = create_run("filesystem", scope)
    
    filesystem_source.LOSEME_DATA_DIR = tmp_path
    filesystem_source.LOSEME_SOURCE_ROOT_HOST = tmp_path

    # Initial document
    doc1 = tmp_path / "doc1.md"
    doc1.write_text("first document")

    # First ingestion: create run
    result_1 = ingest_filesystem_scope(scope, run.id, resume=False)

    assert result_1.documents_discovered == 1
    assert result_1.documents_indexed == 1

    # Add a new document after the run already exists
    doc2 = tmp_path / "doc2.md"
    doc2.write_text("second document")

    # Resume same run
    result_2 = ingest_filesystem_scope(scope, run.id, resume=True)

    # Both documents are discovered,
    # but only the new one should be indexed
    assert result_2.documents_discovered == 2
    assert result_2.documents_indexed == 1

def test_resume_after_cancelled_run(tmp_path):
    init_db()

    scope = IndexingScope(directories=[tmp_path])
    run = create_run("filesystem", scope)
    
    filesystem_source.LOSEME_DATA_DIR = tmp_path
    filesystem_source.LOSEME_SOURCE_ROOT_HOST = tmp_path

    # Create documents
    for i in range(3):
        (tmp_path / f"doc{i}.md").write_text(f"doc {i}")

    # Cancel after first document
    with pytest.raises(IngestionCancelled):
        ingest_filesystem_scope(scope, run.id, resume=False, stop_after=1)

    # Resume run
    result = ingest_filesystem_scope(scope, run.id, resume=True)

    # All docs discovered, remaining indexed
    assert result.documents_discovered == 3
    assert result.documents_indexed == 2

