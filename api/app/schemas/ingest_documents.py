from pydantic import BaseModel
from typing import List, Dict, Any

class IngestedChunk(BaseModel):
    index: int
    text: str
    metadata: Dict[str, Any] = {}

class IngestedDocument(BaseModel):
    document_id: str
    source_type: str
    device_id: str
    source_path: str
    checksum: str
    metadata: Dict[str, Any] = {}
    chunks: List[IngestedChunk]

class IngestDocumentsRequest(BaseModel):
    documents: List[IngestedDocument]

