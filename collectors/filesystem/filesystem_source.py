# collectors/filesystem/filesystem_source.py
from pathlib import Path
from typing import List
from src.domain.ingestion import IngestionSource
from src.domain.models import Document, IndexingScope
import hashlib

class FilesystemIngestionSource(IngestionSource):
    """
    Filesystem-based ingestion source implementing the pull-based, resumable interface.
    """

    def list_documents(self, scope: IndexingScope) -> List[str]:
        file_paths = []
        for directory in scope.directories:
            if not directory.exists() or not directory.is_dir():
                continue
            for path in directory.rglob('*'):
                if path.is_file():
                    # Apply simple include/exclude patterns
                    if scope.include_patterns and not any(path.match(pat) for pat in scope.include_patterns):
                        continue
                    if any(path.match(pat) for pat in scope.exclude_patterns):
                        continue
                    file_paths.append(str(path))
        return file_paths

    def read_document(self, doc_id: str) -> Document:
        path = Path(doc_id)
        with open(path, 'rb') as f:
            content = f.read()
        checksum = hashlib.sha256(content).hexdigest()
        return Document(
            id=str(path.resolve()),
            source='filesystem',
            path=path.resolve(),
            metadata={'size': len(content)},
            checksum=checksum
        )

    def supports_resume(self) -> bool:
        return True

