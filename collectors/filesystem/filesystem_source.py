import os
from pathlib import Path
from typing import List, Optional
import hashlib
from datetime import datetime
from src.domain.models import Document, FilesystemIndexingScope
from src.domain.ids import make_logical_document_id, make_source_instance_id
from src.domain.extraction.registry import ExtractorRegistry
from fnmatch import fnmatch
import logging
import warnings

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

device_id = os.environ.get("LOSEME_DEVICE_ID")
if device_id is None:
    warnings.warn("LOSEME_DEVICE_ID environment variable is not set. Defaulting to 'unknown_device'.", UserWarning)
    device_id = "unknown_device"

LOSEME_DATA_DIR = Path(os.environ.get("LOSEME_DATA_DIR"))
if LOSEME_DATA_DIR is None:
    warnings.warn("LOSEME_DATA_DIR environment variable is not set. Defaulting to '/data'.", UserWarning)

LOSEME_SOURCE_ROOT_HOST = Path(os.environ.get("LOSEME_SOURCE_ROOT_HOST"))
if LOSEME_SOURCE_ROOT_HOST is None:
    warnings.warn("LOSEME_SOURCE_ROOT_HOST environment variable is not set. Defaulting to '/host_data'.", UserWarning)

class FilesystemIngestionSource:
    def __init__(self, 
                 scope: FilesystemIndexingScope,
                 extractor_registry: ExtractorRegistry
                 ):
        self.scope = scope
        self.extractor_registry = extractor_registry

    def list_documents(self) -> List[Document]:
        """
        List all documents in the scope, optionally starting after a given document ID.
        """
        docs = []

        assert device_id is not None, "LOSEME_DEVICE_ID environment variable must be set."
        
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

            logger.debug(f"Including path {path}.")
        
            extracted = self.extractor_registry.extract(path)
            if extracted is None:
                logger.debug(f"No extractor found for path {path}, skipping.")
                continue

            document_checksum = hashlib.sha256(
                   extracted.text.strip().encode("utf-8")
                   ).hexdigest()

            doc_id = make_logical_document_id(
                    text=extracted.text,
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
                        checksum=document_checksum,
                        created_at=datetime.fromtimestamp(path.stat().st_ctime),
                        updated_at=datetime.fromtimestamp(path.stat().st_mtime),
                        metadata={
                            **extracted.metadata,
                            "relative_path": rel_path,
                            "size": path.stat().st_size,
                            "content_type": extracted.content_type,
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

        # Check if self.scope.directories is actually a file
        if len(self.scope.directories) == 1 and self.scope.directories[0].is_file():
            root = self.scope.directories[0].parent
            path = self.scope.directories[0]
            all_files.append((root, path))
            return all_files
            
        for directory in self.scope.directories:
            root = Path(directory)
            for path in root.rglob("*"):
                if path.is_file():
                    all_files.append((root, path))

        return sorted(all_files, key=lambda x: str(x[1]))
