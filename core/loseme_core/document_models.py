import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
from typing_extensions import Literal
from .ids import make_source_instance_id

class DocumentPart(BaseModel):
    text: Optional[str] = None
    document_part_id: str
    source_type: str
    checksum: str
    device_id: str
    source_path: str
    source_instance_id: str
    unit_locator: str
    content_type: str
    extractor_name: str
    extractor_version: str
    metadata_json: Optional[Dict[str, Any]] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    scope_json: dict = Field(default_factory=dict)
        
    @field_validator('scope_json')
    def validate_scope_json(cls, v):
        if not isinstance(v, dict):
            raise ValueError('scope_json must be a dictionary')
        return v

class Document(BaseModel):
    id: str
    source_type: Literal["filesystem", "thunderbird"]
    source_id: str # logical id that uniquely identifies the source of this document, e.g. "filesystem:/path/to/file.txt" or "thunderbird:message-id"
    device_id: str
    source_path: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    checksum: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    parts: Optional[List[DocumentPart]] = Field(default_factory=list)

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

    def add_part(self, part: DocumentPart):
        if self.parts is None:
            self.parts = []
        self.parts.append(part)
    
    @classmethod
    def from_dict(cls, data: dict):
        document = cls(
            id=data["id"],
            source_type=data["source_type"],
            source_id=data["source_id"],
            device_id=data["device_id"],
            source_path=data["source_path"],
            metadata=data.get("metadata", {}),
            checksum=data["checksum"],
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )
        for part in data.get("parts", []):
            document.add_part(DocumentPart(**part))
        return document

    @classmethod
    def deserialize(cls, data: dict):
        raise NotImplementedError("Document.deserialize is not implemented. Use the appropriate subclass based on source_type.")

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
    source_path: str
    text: Optional[str] = None
    document_part_id: str
    device_id: str
    unit_locator: str
    index: int
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('id', 'document_part_id')
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


