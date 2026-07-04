from pathlib import Path
from pydantic import BaseModel, Field
from typing import Literal, Optional, List
from loseme_core.scope_models import IndexingScope
from loseme_core.document_models import Document
from loseme_core.ids import make_paperless_source_id

import json
import hashlib


class PaperlessDocument(Document):
    """Document representation for Paperless-ngx sources."""
    
    paperless_document_id: str
    
    @classmethod
    def from_dict(cls, data: dict) -> "PaperlessDocument":
        """Create a PaperlessDocument from a dictionary."""
        paperless_doc = cls(
            id=data["id"],
            source_type=data["source_type"],
            source_id=data["source_id"],
            device_id=data["device_id"],
            source_path=data["source_path"],
            metadata=data.get("metadata", {}),
            checksum=data["checksum"],
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            paperless_document_id=data["paperless_document_id"],
        )
        for part in data.get("parts", []):
            from src.sources.base.models import DocumentPart
            paperless_doc.add_part(DocumentPart(**part))

        return paperless_doc


class PaperlessIndexingScope(IndexingScope):
    """
    Indexing scope for Paperless-ngx document management system.
    
    Paperless-ngx is a server-side source, so this scope only references
    a connection_id and filter information, not credentials.
    """
    type: Literal["paperless"] = "paperless"
    
    # Reference to the stored connection (credentials are stored separately)
    connection_id: str
    
    # Filter options - None means no filtering (all documents)
    tag_ids: Optional[List[int]] = Field(default=None, description="Filter by tag IDs")
    correspondent_ids: Optional[List[int]] = Field(default=None, description="Filter by correspondent IDs")
    document_type_ids: Optional[List[int]] = Field(default=None, description="Filter by document type IDs")
    
    def normalized(self) -> dict:
        """Return a normalized dictionary representation for consistent hashing."""
        return {
            "type": self.type,
            "connection_id": self.connection_id,
            "tag_ids": sorted(self.tag_ids) if self.tag_ids else None,
            "correspondent_ids": sorted(self.correspondent_ids) if self.correspondent_ids else None,
            "document_type_ids": sorted(self.document_type_ids) if self.document_type_ids else None,
        }

    def hash(self) -> str:
        """Generate a stable hash for this scope."""
        normalized_json = json.dumps(self.normalized(), sort_keys=True, default=str)
        return hashlib.sha256(normalized_json.encode()).hexdigest()

    def locator(self) -> str:
        """Return a locator that uniquely identifies this Paperless source."""
        return f"paperless:{self.connection_id}:{self.hash()}"

    def serialize(self) -> dict:
        """Serialize the scope to a dictionary for storage."""
        return {
            "type": self.type,
            "connection_id": self.connection_id,
            "tag_ids": self.tag_ids,
            "correspondent_ids": self.correspondent_ids,
            "document_type_ids": self.document_type_ids,
        }

    @classmethod
    def deserialize(cls, data: dict) -> "PaperlessIndexingScope":
        """Deserialize a PaperlessIndexingScope from a dictionary."""
        return cls(
            connection_id=data["connection_id"],
            tag_ids=data.get("tag_ids"),
            correspondent_ids=data.get("correspondent_ids"),
            document_type_ids=data.get("document_type_ids"),
        )


class PaperlessIngestRequest(BaseModel):
    """Request model for creating a Paperless ingestion source."""
    connection_id: str = Field(..., description="ID of the Paperless connection")
    tag_ids: Optional[List[int]] = Field(default=None, description="Filter by tag IDs")
    correspondent_ids: Optional[List[int]] = Field(default=None, description="Filter by correspondent IDs")
    document_type_ids: Optional[List[int]] = Field(default=None, description="Filter by document type IDs")


