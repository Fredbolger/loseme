from pathlib import Path
from typing import List, Optional
from src.domain.models import Document, IndexingScope

class FilesystemIngestionSource:
    def __init__(self, scope: IndexingScope):
        self.scope = scope

    def list_documents(self, after: Optional[str] = None) -> List[Document]:
        """
        List all documents in the scope, optionally starting after a given document ID.
        """
        docs = []
        start = after is None
        for path in self._walk_files():
            doc_id = str(path)
            if after and not start:
                if doc_id == after:
                    start = True
                continue
            docs.append(Document(id=doc_id, path=path, source="filesystem"))
        return docs

    def _walk_files(self):
        """
        Walk through all files in scope.directories matching include/exclude patterns.
        Returns sorted paths to ensure resumable indexing works consistently.
        """
        all_files = []
        for directory in self.scope.directories:
            for path in Path(directory).rglob("*"):
                if path.is_file():
                    all_files.append(path)
        # Sort paths lexicographically
        return sorted(all_files)

