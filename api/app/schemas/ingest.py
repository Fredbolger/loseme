from pydantic import BaseModel, Field
from typing import Optional, Dict


class IngestRequest(BaseModel):
    source: str = Field(..., description="Ingestion source type (e.g. filesystem)")
    path: str = Field(..., description="Source path or identifier")
    metadata: Optional[Dict[str, str]] = Field(
        default=None, description="Optional user metadata"
    )


class IngestResponse(BaseModel):
    accepted: bool
    message: str

