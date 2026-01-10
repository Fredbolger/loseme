import os
from pathlib import Path
from typing import List, Optional
import hashlib
from datetime import datetime
from src.domain.models import Document, IndexingScope
from src.domain.ids import make_logical_document_id, make_source_instance_id
from src.domain.extraction.registry import ExtractorRegistry
from fnmatch import fnmatch
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class FilesystemIngestionSource:
    def __init__(self, 
                 scope: IndexingScope,
                 extractor_registry: ExtractorRegistry
                 ):
        self.scope = scope
        self.extractor_registry = extractor_registry

    def list_documents(self, after: Optional[str] = None) -> List[Document]:
        """
        List all documents in the scope, optionally starting after a given document ID.
        """
        docs = []
        start = after is None

        device_id = os.environ.get("LOSEME_DEVICE_ID")

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

            if after and not start:
                if doc_id == after:
                    start = True
                continue

            logger.debug(f"Including path {path}.")
        
            result = self.extractor_registry.extract(path)
            if result is None:
                continue
   
            doc_id = make_logical_document_id(
                    text=result.text
            )
            source_instance_id = make_source_instance_id(
                    source_type="filesystem",
                    source_path=path,
                    device_id=device_id,
            )

            docs.append(
                    Document(
                        id=doc_id,
                        source_type="filesystem",
                        source_id=source_instance_id,
                        device_id=device_id,
                        source_path=str(path),
                        checksum=doc_id,
                        created_at=datetime.fromtimestamp(path.stat().st_ctime),
                        updated_at=datetime.fromtimestamp(path.stat().st_mtime),
                        metadata={
                            **result.metadata,
                            "relative_path": rel_path,
                            "size": path.stat().st_size,
                            "content_type": result.content_type,
                        },
                    )
            )


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
