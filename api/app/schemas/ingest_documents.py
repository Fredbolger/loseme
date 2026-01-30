from pydantic import BaseModel
from typing import List, Dict, Any
from src.domain.models import Chunk, Document

class IngestedDocument(Document):
    pass 

class IngestDocumentsRequest(BaseModel):
    documents: List[IngestedDocument]
    run_id: str
