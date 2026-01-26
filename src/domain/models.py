from __future__ import annotations
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import Literal
from dataclasses import dataclass
from abc import abstractmethod
from src.domain.ids import make_source_instance_id, make_thunderbird_source_id

import logging
logger = logging.getLogger(__name__)

class Document(BaseModel):
    id: str
    source_type: Literal["filesystem", "thunderbird"]
    source_id: str
    device_id: str
    source_path: str
    text: str
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
            data["source_id"] = make_source_instance_id(...)
        super().__init__(**data)


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

class EmailDocument(Document):
    mbox_path: str
    message_id: str

    @model_validator(mode="before")
    @classmethod
    def build_thunderbird_ids(cls, data: dict):
        if data.get("source_type") != "thunderbird":
            return data

        required = ("device_id", "mbox_path", "message_id")
        if not all(k in data for k in required):
            raise ValueError("Thunderbird EmailDocument missing required fields")

        data["source_id"] = make_thunderbird_source_id(
            device_id=data["device_id"],
            mbox_path=data["mbox_path"],
            message_id=data["message_id"],
        )

        # logical but honest source_path
        data["source_path"] = f"{Path(data['mbox_path']).name}/{data['message_id']}"

        return data

class Chunk(BaseModel):
    id: str
    source_type: Literal["filesystem", "thunderbird"]
    document_id: str
    device_id: str
    index: int
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('id', 'document_id')
    def ids_must_not_be_empty(cls, v):
        if not v:
            raise ValueError('IDs must not be empty')
        return v
    @field_validator('source_type')
    def source_type_must_be_valid(cls, v):
        if v not in ["filesystem", "thunderbird"]:
            raise ValueError('source_type must be either "filesystem" or "thunderbird"')
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

    @classmethod
    def deserialize(cls, data: dict) -> "IndexingScope":
        scope_type = data.get("type")

        if scope_type == "filesystem":
            return FilesystemIndexingScope.deserialize(data)

        if scope_type == "thunderbird":
            return ThunderbirdIndexingScope.deserialize(data)

        raise ValueError(f"Unknown scope type: {scope_type}")

class FilesystemIndexingScope(IndexingScope):
    type: Literal["filesystem"] = "filesystem"

    directories: list[Path] = Field(default_factory=list)
    include_patterns: list[str] = Field(default_factory=list)
    exclude_patterns: list[str] = Field(default_factory=list)

    def normalized(self) -> dict:
        return {
            "directories": sorted(str(p.resolve()) for p in self.directories),
            "include_patterns": sorted(self.include_patterns),
            "exclude_patterns": sorted(self.exclude_patterns),
        }

    def hash(self) -> str:
        normalized_json = json.dumps(self.normalized(), sort_keys=True)
        return hashlib.sha256(normalized_json.encode()).hexdigest()

    def serialize(self) -> dict:
        return {
            "type": self.type,
            "directories": [str(p) for p in self.directories],
            "include_patterns": self.include_patterns,
            "exclude_patterns": self.exclude_patterns,
        }

    @classmethod
    def deserialize(cls, data: dict) -> "FilesystemIndexingScope":
        raw_dirs = data.get("directories", [])
        logger.debug(f"Deserializing directories: {raw_dirs!r}")

        if isinstance(raw_dirs, (str, Path)):
            raw_dirs = [raw_dirs]

        if not isinstance(raw_dirs, list):
            raise ValueError("directories must be a path or list of paths")

        directories = [Path(p) for p in raw_dirs]

        # Guard against character explosion (belt + suspenders)
        if any(len(str(p)) == 1 for p in directories):
            raise ValueError(f"Invalid directories value: {raw_dirs!r}")
        
        return cls(
            directories=directories,
            include_patterns=data.get("include_patterns", []),
            exclude_patterns=data.get("exclude_patterns", []),
        )

class ThunderbirdIndexingScope(IndexingScope):
    type: Literal["thunderbird"] = "thunderbird"
    mbox_path: str
    ignore_patterns: Optional[List[dict]] = None

    def serialize(self) -> dict:
        return {
            "type": self.type,
            "mbox_path": self.mbox_path,
            "ignore_patterns": self.ignore_patterns,
        }

    @classmethod
    def deserialize(cls, data: dict) -> "ThunderbirdIndexingScope":
        return cls(
            mbox_path=data["mbox_path"],
            ignore_patterns=data.get("ignore_patterns"),
        )

class IndexingRun(BaseModel):
    id: str
    scope: IndexingScope
    start_time: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    status: Literal['pending', 'running', 'completed', 'interrupted']
    last_document_id: Optional[str] = None
    discovered_document_count: int = 0
    indexed_document_count: int = 0
    stop_requested: bool = False

    @field_validator('id')
    def id_must_not_be_empty(cls, v):
        if not v:
            raise ValueError('IndexingRun id must not be empty')
        return v


class GenericIngestRequest(BaseModel):
    type: str  # "filesystem" | "thunderbird"
    data: Dict[str, Any]  # whatever extra parameters

    @field_validator('type')
    def type_must_be_valid(cls, v):
        if v not in ["filesystem", "thunderbird"]:
            raise ValueError('type must be either "filesystem" or "thunderbird"')
        return v

class FilesystemIngestRequest(BaseModel):
    directories: list[str] = []
    recursive: bool = True
    include_patterns: list[str] = []
    exclude_patterns: list[str] = []

class ThunderbirdIngestRequest(BaseModel):
    mbox_path: str = "" 
    ignore_patterns: Optional[List[dict]] = None

class IngestionSource(BaseModel):
    scope: Any  # Could be IndexingScope or subclass
    should_stop: Callable[[], bool]

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
        from collectors.filesystem.filesystem_source import FilesystemIngestionSource
        from collectors.thunderbird.thunderbird_source import ThunderbirdIngestionSource

        if scope.__class__.__name__ == "FilesystemIndexingScope":
            return FilesystemIngestionSource(scope=scope, should_stop=should_stop)
        elif scope.__class__.__name__ == "ThunderbirdIndexingScope":
            return ThunderbirdIngestionSource(scope=scope, should_stop=should_stop)
        else:
            raise ValueError(f"No ingestion source for scope type: {type(scope)}")
