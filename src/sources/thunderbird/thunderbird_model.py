from pathlib import Path
from pydantic import BaseModel, model_validator
from typing import Literal, Optional, List
from src.sources.base.models import Document, Chunk, IndexingScope, IngestionSource, IngestRequest
from src.core.ids import make_thunderbird_source_id
from src.sources.base.registry import indexing_scope_registry


class ThunderbirdDocument(Document):
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

    @classmethod
    def from_dict(cls, data: dict) -> "ThunderbirdDocument":
        thunderbird_doc = cls(
            id=data["id"],
            checksum=data["checksum"],
            source_type=data["source_type"],
            source_id=data["source_id"],
            device_id=data["device_id"],
            source_path=data["source_path"],
            metadata=data.get("metadata", {}),
            mbox_path=data["mbox_path"],
            message_id=data["message_id"],
        )
        for part in data.get("parts", []):
            from src.sources.base.models import DocumentPart
            thunderbird_doc.add_part(DocumentPart(**part))

        return thunderbird_doc

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
    
    def locator(self) -> str:
        return self.mbox_path

    @classmethod
    def deserialize(cls, data: dict) -> "ThunderbirdIndexingScope":
        return cls(
            mbox_path=data["mbox_path"],
            ignore_patterns=data.get("ignore_patterns"),
        )

class ThunderbirdIngestRequest(BaseModel):
    mbox_path: str = "" 
    ignore_patterns: Optional[List[dict]] = None

indexing_scope_registry.register_scope("thunderbird", ThunderbirdIndexingScope)

