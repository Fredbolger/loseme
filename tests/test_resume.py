import pytest
from pathlib import Path
import hashlib

from storage.metadata_db.db import init_db
from storage.metadata_db.indexing_runs import create_run, load_latest_run
from storage.metadata_db.processed_documents import mark_processed, is_processed
from src.domain.models import IndexingScope
from src.domain.ids import make_logical_document_id, make_source_instance_id


@pytest.fixture
def setup_db():
    init_db()
    yield


def hash_content(text: str) -> str:
    """Hash canonical extracted text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_document_not_reprocessed(setup_db):
    scope = IndexingScope(directories=[Path("/docs")])
    run = create_run("filesystem", scope)

    device_id = "test-device"

    # Stable document identity
    doc_path = Path("/docs/test_doc.md")

    # Canonical extracted text hash
    content = "This is a test document."
    source_instance_id = make_source_instance_id(
            source_type="filesystem",
            device_id=device_id,
            source_path=doc_path
    )
    doc_id = make_logical_document_id(content)

    # Mark document version as processed
    mark_processed(run.id, source_instance_id, doc_id)

    # Reload run as if resuming
    resumed_run = load_latest_run("filesystem", scope)

    # Same document + same content must be recognized
    assert is_processed(resumed_run.id, source_instance_id, doc_id)

    # Simulate indexing loop
    other_doc_path = Path("/docs/another_doc.md")
    other_content = "dummy content"
    other_source_instance_id = make_source_instance_id(
            source_type="filesystem",
            device_id=device_id,
            source_path=other_doc_path
    )
    other_doc_id = make_logical_document_id(other_content)

    documents_to_index = [
            (source_instance_id, doc_id),  # same document, same content
            (other_source_instance_id, other_doc_id),  # new document
    ]
    # We now have two documents to consider with different content
    # but only one should be processed. because the first one was already processed.

    processed_docs = []
    for d_id, d_hash in documents_to_index:
        if not is_processed(resumed_run.id, d_id, d_hash):
            processed_docs.append(d_id)

    # Assertions
    assert len(processed_docs) == 1  # Only the new document should be processed
    assert processed_docs[0] == other_source_instance_id

