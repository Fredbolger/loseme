from pydantic import BaseModel, Field, validator
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Any

class Document(BaseModel):
    id: str
    source: str
    path: Optional[Path] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    checksum: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @validator('id')
    def id_must_not_be_empty(cls, v):
        if not v:
            raise ValueError('Document id must not be empty')
        return v

class Chunk(BaseModel):
    id: str
    document_id: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator('id', 'document_id')
    def ids_must_not_be_empty(cls, v):
        if not v:
            raise ValueError('IDs must not be empty')
        return v

class IndexingScope(BaseModel):
    directories: List[Path] = Field(default_factory=list)
    include_patterns: List[str] = Field(default_factory=list)
    exclude_patterns: List[str] = Field(default_factory=list)

class IndexingRun(BaseModel):
    id: str
    scope: IndexingScope
    start_time: datetime = Field(default_factory=datetime.utcnow)
    status: str = 'pending'  # 'pending', 'running', 'completed', 'interrupted'
    processed_documents: List[str] = Field(default_factory=list)

    @validator('id')
    def id_must_not_be_empty(cls, v):
        if not v:
            raise ValueError('IndexingRun id must not be empty')
        return v

