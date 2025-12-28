from pathlib import Path
from typing import List, Optional
from src.domain.models import Document, IndexingScope
from fnmatch import fnmatch
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class FilesystemIngestionSource:
    def __init__(self, scope: IndexingScope):
        self.scope = scope

    def list_documents(self, after: Optional[str] = None) -> List[Document]:
        """
        List all documents in the scope, optionally starting after a given document ID.
        """
        docs = []
        start = after is None

        logger.debug(f"files are: {list(self._walk_files())}")
        for root, path in self._walk_files():
            rel_path = path.relative_to(root).as_posix()
            
            logger.debug(f"Checking path {path} with relative path {rel_path}.")
            logger.debug(f"Exclude patterns: {self.scope.exclude_patterns}")

            if self.scope.exclude_patterns and any(
                fnmatch(rel_path, pattern) for pattern in self.scope.exclude_patterns
            ):
                logger.debug(f"Excluding path {path} due to exclude patterns.")
                continue

            if self.scope.include_patterns and not any(
                fnmatch(rel_path, pattern) for pattern in self.scope.include_patterns
            ):
                logger.debug(f"Excluding path {path} due to include patterns.")
                continue

            doc_id = str(path)

            if after and not start:
                if doc_id == after:
                    start = True
                continue

            logger.debug(f"Including path {path}.")
            docs.append(Document(id=doc_id, path=path, source="filesystem"))

        return docs

    def _walk_files(self):
        """
        Walk through all files in scope.directories.
        Returns (root, path) tuples, sorted for stable resumable indexing.
        """
        all_files = []
        for directory in self.scope.directories:
            root = Path(directory)
            for path in root.rglob("*"):
                if path.is_file():
                    all_files.append((root, path))

        return sorted(all_files, key=lambda x: str(x[1]))
