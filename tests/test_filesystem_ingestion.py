import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

from pathlib import Path
from unittest.mock import patch
from collectors.filesystem.filesystem_source import FilesystemIngestionSource
from src.domain.models import FilesystemIndexingScope
from pipeline.extraction.registry import ExtractorRegistry
from pipeline.extraction.plaintext import PlainTextExtractor
import pytest

@pytest.fixture(autouse=True)
def fake_loseme_paths(tmp_path, monkeypatch):
    fake_data_dir = tmp_path
    fake_host_root = tmp_path

    monkeypatch.setattr(
        "collectors.filesystem.filesystem_source.LOSEME_DATA_DIR",
        fake_data_dir,
    )
    monkeypatch.setattr(
        "collectors.filesystem.filesystem_source.LOSEME_SOURCE_ROOT_HOST",
        fake_host_root,
    )

def test_filesystem_excludes_paths(tmp_path):
    # Arrange: create real files on disk
    root = tmp_path

    included = root / "file1.txt"
    excluded_dir = root / "IgnorePath"
    excluded_dir.mkdir()
    excluded = excluded_dir / "file2.txt"

    included.write_text("included content")
    excluded.write_text("excluded content")
    
    # Now two files exist under the paths: root/file1.txt and root/IgnorePath/file2.txt

    scope = FilesystemIndexingScope(
        type="filesystem",
        directories=[root],
        include_patterns=[],
        exclude_patterns=["IgnorePath/*"],
    )

    registry = ExtractorRegistry([
        PlainTextExtractor(),
    ])
 
    source = FilesystemIngestionSource(
            scope=scope,
            should_stop=lambda: False,
    )

    # Act
    docs = [doc for doc in source.iter_documents()]

    # Assert
    assert len(docs) == 1
    assert docs[0].source_path == str(included)
