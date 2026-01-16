from __future__ import annotations
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
from typing_extensions import Literal
from dataclasses import dataclass

class Document(BaseModel):
    id: str
    source_type: Literal['filesystem']
    source_id: str
    device_id: str
    source_path: str
    docker_path: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    checksum: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    

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
        if v != 'filesystem':
            raise ValueError("source_type must be 'filesystem'")
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
    directories: list[Path] = []
    include_patterns: list[str] = []
    exclude_patterns: list[str] = []

    def normalized(self) -> dict:
        return {
            "directories": sorted(str(p.resolve()) for p in self.directories),
            "include_patterns": sorted(self.include_patterns),
            "exclude_patterns": sorted(self.exclude_patterns),
        }

    def hash(self) -> str:
        normalized_json = json.dumps(self.normalized(), sort_keys=True)
        return hashlib.sha256(normalized_json.encode()).hexdigest()


class IndexingRun(BaseModel):
    id: str
    scope: IndexingScope
    start_time: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    status: Literal['pending', 'running', 'completed', 'interrupted']
    last_document_id: Optional[str] = None

    @field_validator('id')
    def id_must_not_be_empty(cls, v):
        if not v:
            raise ValueError('IndexingRun id must not be empty')
        return v

class FilesystemIngestRequest(BaseModel):
    directories: list[str] = []
    recursive: bool = True
    include_patterns: list[str] = []
    exclude_patterns: list[str] = []

