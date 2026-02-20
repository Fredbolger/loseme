import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

from pathlib import Path
from unittest.mock import patch
from src.sources.filesystem import FilesystemIndexingScope, FilesystemIngestionSource
from src.sources.base import extractor_registry
import pytest
import tempfile

# After imports
for name, log_obj in logging.root.manager.loggerDict.items():
    if isinstance(log_obj, logging.Logger):
        log_obj.setLevel(logging.DEBUG)
        log_obj.propagate = True

def test_filesystem_excludes_paths(write_files_to_disk):
    root, all_documents, all_ignored_documents = write_files_to_disk

    scope = FilesystemIndexingScope(
        type="filesystem",
        directories=[root],
        include_patterns=[],
        exclude_patterns=["IgnorePath/*"],
    )

    source = FilesystemIngestionSource(
            scope=scope,
            should_stop=lambda: False,
    )
    
    logger.debug(f"Testing with source: {source}")

    # Act
    docs = [doc for doc in source.iter_documents()]

    # Assert
    assert len(docs) == len(all_documents) - len(all_ignored_documents)

if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        test_filesystem_excludes_paths(tmp_path)
