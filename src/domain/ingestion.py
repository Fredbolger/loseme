from abc import ABC, abstractmethod
from typing import List
from .models import Document, IndexingScope

class IngestionSource(ABC):
    """
    Abstract interface for any pull-based ingestion source.
    Implementations should list items within the given scope and return Document objects.
    Ingestion should be incremental, resumable, and traceable.
    """

    @abstractmethod
    def list_documents(self, scope: IndexingScope) -> List[str]:
        """Return a list of identifiers/paths for all documents in the scope."""
        pass
    
    '''
    @abstractmethod
    def read_document(self, doc_id: str) -> Document:
        """Given a document identifier, read and return the Document object."""
        pass

    @abstractmethod
    def supports_resume(self) -> bool:
        """Return True if this source can support incremental/resumable ingestion."""
        pass
    '''
