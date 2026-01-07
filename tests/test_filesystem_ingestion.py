import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

from pathlib import Path
from unittest.mock import patch
from collectors.filesystem.filesystem_source import FilesystemIngestionSource
from src.domain.models import IndexingScope

def test_filesystem_excludes_paths(tmp_path):
    # Arrange: create real files on disk
    root = tmp_path

    included = root / "file1.txt"
    excluded_dir = root / "IgnorePath"
    excluded_dir.mkdir()
    excluded = excluded_dir / "file2.txt"

    included.write_text("included content")
    excluded.write_text("excluded content")

    scope = IndexingScope(
        directories=[root],
        include_patterns=[],
        exclude_patterns=["IgnorePath/*"],
    )

    source = FilesystemIngestionSource(scope)

    # Act
    docs = source.list_documents()

    # Assert
    assert len(docs) == 1
    assert docs[0].path == included
    assert docs[0].content == "included content"

