import pytest
from pathlib import Path
from datetime import datetime

from src.domain.models import Document
from src.domain.ids import make_logical_document_id
from storage.metadata_db.db import init_db
from storage.metadata_db.indexing_runs import (
    create_run,
    update_status,
    update_checkpoint,
    load_latest_interrupted,
)
from collectors.filesystem.filesystem_source import FilesystemIngestionSource
from src.domain.models import FilesystemIndexingScope


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    monkeypatch.setenv("LOSEME_DEVICE_ID", "test-device")
    monkeypatch.setenv("LOSEME_DATA_DIR", str(tmp_path))
    init_db()
    yield


def _write_file(root: Path, name: str, content: str) -> Path:
    p = root / name
    p.write_text(content)
    return p


def test_resume_pipeline_filesystem(tmp_path):
    """
    Pipeline-level resume test (NO API, NO CLI).

    Verifies that:
    - a filesystem indexing run can be interrupted
    - checkpoint is persisted
    - resumed run continues from last checkpoint
    """

    # --- arrange filesystem ---
    data_root = tmp_path / "data"
    data_root.mkdir()

    f1 = _write_file(data_root, "a.txt", "hello world")
    f2 = _write_file(data_root, "b.txt", "second file")
    f3 = _write_file(data_root, "c.txt", "third file")

    scope = FilesystemIndexingScope(
        directories=[data_root],
        recursive=True,
        include_patterns=[],
        exclude_patterns=[],
    )

    # --- create interrupted run ---
    run = create_run("filesystem", scope)

    source = FilesystemIngestionSource(scope, should_stop=lambda: False)
    docs = list(source.iter_documents())

    assert len(docs) == 3

    # simulate partial progress
    processed = docs[:2]
    last_doc = processed[-1]

    update_checkpoint(run.id, last_doc.id)
    update_status(run.id, "interrupted")

    # --- act: resume ---
    resumed = load_latest_interrupted("filesystem")
    assert resumed is not None

    resumed_scope = resumed.scope
    resumed_source = FilesystemIngestionSource(resumed_scope, should_stop=lambda: False)

    resumed_docs = list(resumed_source.iter_documents())

    # --- assert resume behavior ---
    resumed_ids = {d.id for d in resumed_docs}
    processed_ids = {d.id for d in processed}

    # resumed iteration still sees all docs
    assert processed_ids.issubset(resumed_ids)

    # but checkpoint ensures caller can skip already-processed docs
    assert resumed.last_document_id == last_doc.id

