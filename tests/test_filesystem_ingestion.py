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

def test_filesystem_excludes_paths():
    logger.debug("Starting test_filesystem_excludes_paths")
    scope = IndexingScope(
        directories=["/root"],
        include_patterns=[],
        exclude_patterns=["IgnorePath/*"],
    )

    source = FilesystemIngestionSource(scope)

    with patch.object(FilesystemIngestionSource, "_walk_files") as mock_walk:
        mock_walk.return_value = [
            (Path("/root"), Path("/root/file1.txt")),
            (Path("/root"), Path("/root/IgnorePath/file2.txt")),
        ]

        docs = source.list_documents()

    assert len(docs) == 1

