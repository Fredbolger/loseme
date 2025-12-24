from __future__ import annotations
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator


class Document(BaseModel):
    id: str
    source: str
    path: Optional[Path] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    checksum: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator('id')
    def id_must_not_be_empty(cls, v):
        if not v:
            raise ValueError('Document id must not be empty')
        return v


class Chunk(BaseModel):
    id: str
    document_id: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('id', 'document_id')
    def ids_must_not_be_empty(cls, v):
        if not v:
            raise ValueError('IDs must not be empty')
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
    status: str = 'pending'  # 'pending', 'running', 'completed', 'interrupted'
    processed_documents: List[str] = Field(default_factory=list)
    last_document_id: Optional[str] = None

    @field_validator('id')
    def id_must_not_be_empty(cls, v):
        if not v:
            raise ValueError('IndexingRun id must not be empty')
        return v

