from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from src.sources.base.models import Chunk, Document

class IngestedDocument(Document):
    mbox_path: Optional[str] = None
    message_id: Optional[str] = None
    pass 

class IngestDocumentsRequest(BaseModel):
    documents: List[IngestedDocument]
    run_id: str
