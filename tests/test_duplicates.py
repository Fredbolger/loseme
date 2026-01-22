import pytest
import hashlib
from pathlib import Path
from storage.metadata_db.db import init_db
from storage.metadata_db.indexing_runs import create_run, load_latest_run_by_scope 
from storage.metadata_db.processed_documents import mark_processed, is_processed
from src.domain.models import FilesystemIndexingScope

def test_document_not_reprocessed(setup_db):
    """
    Test that a document already marked as processed
    is skipped in a new run.
    """
    # Create scope and run
    scope = FilesystemIndexingScope(type='filesystem',directories=[Path("/docs")])
    run = create_run("filesystem", scope)
    
    # Simulate first document processing
    doc_id = "/docs/test_doc.md"
    content = "This is a test document."
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    mark_processed(str(run.id), str(doc_id), str(content_hash))

    # Reload run as if resuming
    resumed_run = load_latest_run_by_scope(scope)
    
    # The document should be marked as processed
    assert is_processed(str(doc_id), str(content_hash))
    
    # Simulate iterating over documents
    documents_to_index = [doc_id, "/docs/another_doc.md"]
    processed_docs = []
    for doc in documents_to_index:
        if not is_processed(str(doc), str(content_hash)):
            processed_docs.append(doc)

    # The already-processed document should be skipped
    assert doc_id not in processed_docs
    assert "/docs/another_doc.md" in processed_docs
