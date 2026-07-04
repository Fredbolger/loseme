from __future__ import annotations
import datetime
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable
from pydantic import BaseModel, Field, field_validator
from typing_extensions import Literal
from dataclasses import dataclass
from abc import abstractmethod
from loseme_core.ids import make_source_instance_id
from loseme_core.document_models import Document, DocumentPart, Chunk
from loseme_core.scope_models import IndexingScope
from loseme_core.thunderbird_model import ThunderbirdIndexingScope
from loseme_core.filesystem_model import FilesystemIndexingScope
from loseme_core.paperless_model import PaperlessIndexingScope

import logging
logger = logging.getLogger(__name__)


class IndexingRun(BaseModel):
    id: str
    celery_id: str = "0"
    scope: IndexingScope
    start_time: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    status: Literal['pending', 'running', 'completed', 'interrupted', 'failed']
    last_document_id: Optional[str] = None
    discovered_document_count: int = 0
    indexed_document_count: int = 0
    stop_requested: bool = False
    is_discovering: bool = True
    is_indexing: bool = False

    @field_validator('id')
    def id_must_not_be_empty(cls, v):
        if not v:
            raise ValueError('IndexingRun id must not be empty')
        return v

class IngestionSource(BaseModel):
    scope: Any  # Could be IndexingScope or subclass
    should_stop: Callable[[], bool]
    update_if_changed_after: Optional[datetime] = None # Optional datetime to indicate that documents should only be re-ingested if they have changed since this time

    def iter_documents(self) -> List[Any]:
        """Yield documents for ingestion. Must be implemented by subclasses."""
        raise NotImplementedError


    @abstractmethod
    def get_open_descriptor(self, document_id: str) -> OpenDescriptor:
        """
        Describe how this document should be opened by a client.
        Must be pure, no side effects.
        """
        raise NotImplementedError
   
    @abstractmethod
    def extract_by_document_id(self, document_id: str) -> Optional[Document]:
        """
        Extract the full Document by its ID.
        Must be implemented by subclasses.
        """
        raise NotImplementedError

    # Fallback implementation
    def extract_by_document_ids(self, document_ids: List[str]) -> List[Document]:
        """
        Extract multiple Documents by their IDs.
        Fallback to calling extract_by_document_id in a loop if not implemented.
        """
        documents = []
        for doc_id in document_ids:
            doc = self.extract_by_document_id(doc_id)
            if doc is not None:
                documents.append(doc)
        return documents

    @classmethod
    def from_scope(cls, scope: Any, should_stop: Callable[[], bool]) -> "IngestionSource":
        """Factory to return the correct subclass based on scope type."""
        # Direct import without registry
        # Handle StoredScope which has a 'type' field
        if hasattr(scope, 'type'):
            if scope.type == "filesystem":
                from .filesystem_model import FilesystemIngestionSource
                return FilesystemIngestionSource(scope=scope, should_stop=should_stop)
            elif scope.type == "thunderbird":
                from .thunderbird_model import ThunderbirdIngestionSource
                return ThunderbirdIngestionSource(scope=scope, should_stop=should_stop)
            elif scope.type == "paperless":
                from .paperless_model import PaperlessIngestionSource
                return PaperlessIngestionSource(scope=scope, should_stop=should_stop)
        
        # Handle direct scope classes
        if scope.__class__.__name__ == "FilesystemIndexingScope":
            from .filesystem_model import FilesystemIngestionSource
            return FilesystemIngestionSource(scope=scope, should_stop=should_stop)
        elif scope.__class__.__name__ == "ThunderbirdIndexingScope":
            from .thunderbird_model import ThunderbirdIngestionSource
            return ThunderbirdIngestionSource(scope=scope, should_stop=should_stop)
        elif scope.__class__.__name__ == "PaperlessIndexingScope":
            # Paperless ingestion source is server-side only
            # This will be handled by the server's IngestionSource.from_scope override
            from .paperless_model import PaperlessIndexingScope
            # For core usage, we return a placeholder that will be replaced on server
            raise NotImplementedError(f"PaperlessIngestionSource must be used on the server side. Scope: {scope.locator()}")
        
        raise ValueError(f"No ingestion source for scope type: {type(scope)}")

class IngestRequest(BaseModel):
    type: str  # "filesystem" | "thunderbird" | "paperless"
    data: Dict[str, Any]  # whatever extra parameters

    @field_validator('type')
    def type_must_be_valid(cls, v):
        if v not in ["filesystem", "thunderbird", "paperless"]:
            raise ValueError('type must be either "filesystem", "thunderbird", or "paperless"')
        return v

@dataclass
class OpenDescriptor:
    source_type: str              # "filesystem", "url", "thunderbird", ...
    target: str            # path, url, message-id, etc.
    extra: dict | None = None
    os_command: str | None = None

class ProcessableUnit(BaseModel):
    locator: str
    mime_type: str
    checksum: str | None
