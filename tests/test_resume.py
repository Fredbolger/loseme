import pytest
from pathlib import Path
import hashlib

from storage.metadata_db.db import init_db
from storage.metadata_db.indexing_runs import create_run, load_latest_run_by_scope
from storage.metadata_db.processed_documents import mark_processed, is_processed
from src.sources.filesystem import FilesystemIndexingScope
from src.core.ids import make_source_instance_id


@pytest.fixture
def setup_db():
    init_db()
    yield


def hash_content(text: str) -> str:
    """Hash canonical extracted text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_document_not_reprocessed(setup_db):
    scope = FilesystemIndexingScope(type="filesystem",directories=[Path("/docs")])
    run = create_run("filesystem", scope)

    device_id = "test-device"

    # First document
    doc_path = Path("/docs/test_doc.md")
    content = "This is a test document."
    content_checksum = hash_content(content)

    source_instance_id = make_source_instance_id(
        source_type="filesystem",
        device_id=device_id,
        source_path=doc_path,
    )

    # Mark document as already processed
    mark_processed(run.id, source_instance_id, content_checksum)

    # Reload run as if resuming
    resumed_run = load_latest_run_by_scope( scope)

    # Same document + same content must be recognized
    assert is_processed(
        source_instance_id,
        content_checksum,
    )

    # Second (new) document
    other_doc_path = Path("/docs/another_doc.md")
    other_content = "dummy content"
    other_checksum = hash_content(other_content)

    other_source_instance_id = make_source_instance_id(
        source_type="filesystem",
        device_id=device_id,
        source_path=other_doc_path,
    )

    # Simulated indexing candidates:
    # (source_instance_id, content_checksum)
    documents_to_index = [
        (source_instance_id, content_checksum),          # already processed
        (other_source_instance_id, other_checksum),      # new document
    ]

    processed_docs = []
    for sid, checksum in documents_to_index:
        if not is_processed(sid, checksum):
            processed_docs.append(sid)

    # Only the new document should be processed
    assert len(processed_docs) == 1
    assert processed_docs[0] == other_source_instance_id


def test_resume_uses_source_instance_and_checksum(setup_db):
    scope = FilesystemIndexingScope(type="filesystem",directories=[Path("/docs")])
    run = create_run("filesystem", scope)

    source_instance_id = "src-1"
    checksum_v1 = "hash-v1"
    checksum_v2 = "hash-v2"

    mark_processed(run.id, source_instance_id, checksum_v1)

    assert is_processed(source_instance_id, checksum_v1)
    assert not is_processed(source_instance_id, checksum_v2)

