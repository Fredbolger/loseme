import pytest
from pathlib import Path
import hashlib

from storage.metadata_db.db import init_db
from storage.metadata_db.indexing_runs import create_run, load_latest_run
from storage.metadata_db.processed_documents import mark_processed, is_processed
from src.domain.models import IndexingScope

@pytest.fixture
def setup_db():
    init_db()
    yield

def hash_content(content: str) -> str:
    """Helper to compute content hash."""
    return hashlib.sha256(content.encode()).hexdigest()

def test_document_not_reprocessed(setup_db):
    scope = IndexingScope(directories=[Path("/docs")])
    run = create_run("filesystem", scope)

    # First document content and hash
    doc_id = "/docs/test_doc.md"
    content = "This is a test document."
    content_hash = hash_content(content)

    # Mark as processed with hash
    mark_processed(run.id, doc_id, content_hash)

    # Reload run
    resumed_run = load_latest_run("filesystem", scope)

    # Already processed document should be recognized
    assert is_processed(resumed_run.id, doc_id, content_hash)

    # Simulate indexing loop
    documents_to_index = [doc_id, "/docs/another_doc.md"]
    processed_docs = []
    for doc in documents_to_index:
        # Assume same content hash for simplicity
        doc_hash = hash_content("dummy content" if doc != doc_id else content)
        if not is_processed(resumed_run.id, doc, doc_hash):
            processed_docs.append(doc)

    # The already processed doc should be skipped
    assert doc_id not in processed_docs
    assert "/docs/another_doc.md" in processed_docs

