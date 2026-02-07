from __future__ import annotations
import datetime
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import Literal
from dataclasses import dataclass
from abc import abstractmethod
from src.core.ids import make_source_instance_id

import logging
logger = logging.getLogger(__name__)

class Document(BaseModel):
    id: str
    source_type: Literal["filesystem", "thunderbird"]
    source_id: str
    device_id: str
    source_path: str
    text: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    checksum: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


    def __init__(self, **data):
        if (
            "source_id" not in data
            and "source_type" in data
            and "source_path" in data
            and "device_id" in data
        ):
            data["source_id"] = make_source_instance_id(
                source_type=data["source_type"],
                source_path=Path(data["source_path"]),
                device_id=data["device_id"],
            )
        super().__init__(**data)

    def to_dict(self):
        d = self.model_dump()
        d["source_path"] = str(d["source_path"])
        return d

    @field_validator('id')
    def id_must_not_be_empty(cls, v):
        if not v:
            raise ValueError('Document id must not be empty')
        return v
    
    @field_validator('checksum')
    def checksum_must_not_be_empty(cls, v):
        if not v:
            raise ValueError('Document checksum must not be empty')
        return v

    @field_validator('source_type')
    def source_type_must_be_valid(cls, v):
        if v not in ["filesystem", "thunderbird"]:
            raise ValueError('source_type must be either "filesystem" or "thunderbird"')
        return v

    @field_validator('source_path')
    def source_path_must_not_be_empty(cls, v):
        if not v:
            raise ValueError('source_path must not be empty')
        return v

    @field_validator('device_id')
    def device_id_must_not_be_empty(cls, v):
        if not v:
            raise ValueError('device_id must not be empty')
        return v

class Chunk(BaseModel):
    id: str
    source_type: str  # e.g., "text", "image", etc.
    text: Optional[str] = None
    document_id: str
    device_id: str
    index: int
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('id', 'document_id')
    def ids_must_not_be_empty(cls, v):
        if not v:
            raise ValueError('IDs must not be empty')
        return v
    @field_validator('device_id')
    def device_id_must_not_be_empty(cls, v):
        if not v:
            raise ValueError('device_id must not be empty')
        return v
    @field_validator('index')
    def index_must_be_non_negative(cls, v):
        if v < 0:
            raise ValueError('Chunk index must be non-negative')
        return v

class IndexingScope(BaseModel):
    """ 
    Abstract base class for indexing scopes.
    Based on the type field in the dictionary, the appropriate subclass will be instantiated.
    """
    type: str
    
    @abstractmethod
    def locator(self) -> str:
        """Return a locator that uniquely identifies the source of this scope."""
        pass
    
    @classmethod
    def deserialize(cls, data: dict) -> "IndexingScope":
        from .registry import indexing_scope_registry
        scope_type = data.get("type")

        if scope_type == "filesystem":
            return indexing_scope_registry.deserialize(data)
            #return FilesystemIndexingScope.deserialize(data)

        if scope_type == "thunderbird":
            return indexing_scope_registry.deserialize(data)
            #return ThunderbirdIndexingScope.deserialize(data)

        raise ValueError(f"Unknown scope type: {scope_type}")

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
        from .registry import ingestion_source_registry

        if scope.__class__.__name__ == "FilesystemIndexingScope":
            source = ingestion_source_registry.get_source("filesystem")
            return source(scope=scope, should_stop=should_stop)
        elif scope.__class__.__name__ == "ThunderbirdIndexingScope":
            source = ingestion_source_registry.get_source("thunderbird")
            return source(scope=scope, should_stop=should_stop)
        else:
            raise ValueError(f"No ingestion source for scope type: {type(scope)}")

class IngestRequest(BaseModel):
    type: str  # "filesystem" | "thunderbird"
    data: Dict[str, Any]  # whatever extra parameters

    @field_validator('type')
    def type_must_be_valid(cls, v):
        if v not in ["filesystem", "thunderbird"]:
            raise ValueError('type must be either "filesystem" or "thunderbird"')
        return v

@dataclass
class OpenDescriptor:
    source_type: str              # "filesystem", "url", "thunderbird", ...
    target: str            # path, url, message-id, etc.
    extra: dict | None = None
    os_command: str | None = None
