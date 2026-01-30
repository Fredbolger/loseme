import pytest
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(name)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("transformers_modules").setLevel(logging.WARNING)

from src.domain.models import EmailDocument, ThunderbirdIndexingScope
from collectors.thunderbird.thunderbird_source import ThunderbirdIngestionSource
from storage.metadata_db.indexing_runs import (
    create_run,
    update_checkpoint,
    update_status,
    load_latest_interrupted,
)
from storage.metadata_db.processed_documents import get_all_processed
from storage.metadata_db.db import init_db


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    monkeypatch.setenv("LOSEME_DEVICE_ID", "test-device")
    monkeypatch.setenv("LOSEME_DATA_DIR", str(tmp_path))
    init_db()
    yield


def test_email_document_constructor_sets_thunderbird_ids():
    doc = EmailDocument(
        id="doc-1",
        source_type="thunderbird",
        device_id="test-device",
        mbox_path="/home/user/.thunderbird/Inbox",
        message_id="<abc123@example.com>",
        text="Hello world",
        checksum="checksum-1",
        metadata={},
    )

    assert doc.source_type == "thunderbird"
    assert doc.device_id == "test-device"
    assert doc.mbox_path.endswith("Inbox")
    assert doc.message_id == "<abc123@example.com>"
    assert doc.text == "Hello world"

    assert doc.source_id
    assert doc.source_path == "Inbox/<abc123@example.com>"


def test_thunderbird_source_iterates_documents(fake_mbox_path):
    scope = ThunderbirdIndexingScope(
        type="thunderbird",
        mbox_path=fake_mbox_path,
    )

    source = ThunderbirdIngestionSource(scope=scope, should_stop=lambda: False)

    docs = list(source.iter_documents())
    assert len(docs) > 0

    for d in docs[:3]:
        assert d.text
        assert d.source_id


def test_thunderbird_ignore_pattern(fake_mbox_path):
    ignore_patterns = [{"field": "from", "value": "*google.com*"}]

    scope_with_ignore = ThunderbirdIndexingScope(
        type="thunderbird",
        mbox_path=fake_mbox_path,
        ignore_patterns=ignore_patterns,
    )
    scope_without_ignore = ThunderbirdIndexingScope(
        type="thunderbird",
        mbox_path=fake_mbox_path,
    )

    src_ignore = ThunderbirdIngestionSource(scope_with_ignore, should_stop=lambda: False)
    src_plain = ThunderbirdIngestionSource(scope_without_ignore, should_stop=lambda: False)

    plain_docs = {d.source_id: d for d in src_plain.iter_documents()}
    ignore_docs = {d.source_id: d for d in src_ignore.iter_documents()}

    assert plain_docs  # sanity

    ignored = 0
    for sid, plain in plain_docs.items():
        from_val = plain.metadata.get("from") or ""
        ignored_doc = ignore_docs.get(sid)

        if "google.com" in from_val:
            ignored += 1
            # ignored docs must either be missing or altered
            assert ignored_doc is None or ignored_doc.text != plain.text
        else:
            # non-ignored docs must be identical
            assert ignored_doc is not None
            assert ignored_doc.text == plain.text

    assert ignored > 0

def test_thunderbird_resume_pipeline(fake_mbox_path):
    scope = ThunderbirdIndexingScope(
        type="thunderbird",
        mbox_path=fake_mbox_path,
    )

    run = create_run("thunderbird", scope)

    source = ThunderbirdIngestionSource(scope, should_stop=lambda: False)
    docs = list(source.iter_documents())
    assert len(docs) >= 10

    first_batch = docs[:5]
    last_doc = first_batch[-1]

    for d in first_batch:
        pass  # simulate processing

    update_checkpoint(run.id, last_doc.id)
    update_status(run.id, "interrupted")

    resumed = load_latest_interrupted("thunderbird")
    assert resumed is not None
    assert resumed.last_document_id == last_doc.id

    resumed_source = ThunderbirdIngestionSource(resumed.scope, should_stop=lambda: False)
    resumed_docs = list(resumed_source.iter_documents())

    all_ids = {d.id for d in resumed_docs}
    assert last_doc.id in all_ids

