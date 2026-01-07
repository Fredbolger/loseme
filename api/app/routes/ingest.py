from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
from typing import Iterable

from collectors.filesystem.filesystem_source import FilesystemIngestionSource
from src.domain.models import Document, IndexingScope

router = APIRouter(prefix="/ingest", tags=["ingestion"])

class FilesystemIngestRequest(BaseModel):
    path: str
    recursive: bool = True
    include_patterns: list[str] = []
    exclude_patterns: list[str] = []

@router.post("/filesystem")
def ingest_filesystem(req: FilesystemIngestRequest):
    root = Path(req.path)
    include_patterns = req.include_patterns
    exclude_patterns = req.exclude_patterns

    if not root.exists():
        raise HTTPException(status_code=400, detail="Path does not exist")

    scope = IndexingScope(directories=[root],include_patterns=include_patterns, exclude_patterns=exclude_patterns)
    source = FilesystemIngestionSource(scope=scope)
    documents = list(source.list_documents())

    return {
        "status": "ok",
        "documents_ingested": len(documents),
    }

