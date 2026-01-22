import os
from pathlib import Path
from typing import List, Optional, Callable
import hashlib
from datetime import datetime
from src.domain.models import Document, FilesystemIndexingScope, IngestionSource
from src.domain.ids import make_logical_document_id, make_source_instance_id
from src.domain.extraction.registry import ExtractorRegistry
from src.core.wiring import build_extractor_registry
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

class FilesystemIngestionSource(IngestionSource):
    _extractor_registry: ExtractorRegistry = build_extractor_registry()

    def __init__(self, 
                 scope: FilesystemIndexingScope,
                 should_stop: Optional[Callable[[], bool]] = None
                 ):
        super().__init__(scope = scope, should_stop=should_stop)
        self.scope = scope
        self.should_stop = should_stop

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
    
    @property
    def extractor_registry(self) -> ExtractorRegistry:
        return self._extractor_registry

    def iter_documents(self) -> List[Document]:
        """ 
        Iterate over documents in the scope. This should not simply recycle list_documents()
        but actually yield documents one by one for memory efficiency.
        """
        for root_path in self.scope.directories:

            root = Path(root_path)
            for path in root.rglob("*"):
                if self.should_stop():
                    logger.info("Stop requested, terminating filesystem ingestion source.")
                    break

                if path.is_file():
                    rel_path = path.relative_to(root).as_posix()
                    
                    if self.scope.exclude_patterns and any(
                        fnmatch(rel_path, pattern) for pattern in self.scope.exclude_patterns
                    ):
                        continue

                    if self.scope.include_patterns and not any(
                        fnmatch(rel_path, pattern) for pattern in self.scope.include_patterns
                    ):
                        continue

                    extracted = self.extractor_registry.extract(path)
                    if extracted is None:
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

                    yield Document(
                        id=doc_id,
                        source_type="filesystem",
                        source_id=source_instance_id,
                        device_id=device_id,
                        source_path=str(path),
                        text=extracted.text,
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

