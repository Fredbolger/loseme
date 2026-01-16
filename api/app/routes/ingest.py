import os
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from pathlib import Path
from typing import Iterable

from collectors.filesystem.filesystem_source import FilesystemIngestionSource
from src.domain.models import Document, IndexingScope, FilesystemIngestRequest
from src.domain.ids import make_source_instance_id
from src.core.wiring import build_extractor_registry
from storage.metadata_db.indexing_runs import create_run, update_status, update_checkpoint
from storage.metadata_db.processed_documents import mark_processed, is_processed
from api.app.services.ingestion import ingest_filesystem_scope
from storage.metadata_db.db import init_db
import logging

logger = logging.getLogger(__name__)

registry = build_extractor_registry()

def get_data_root() -> Path:
    return Path(
        os.environ.get("LOSEME_DATA_DIR", "/data")
    ).resolve()

router = APIRouter(prefix="/ingest", tags=["ingestion"])

@router.post("/filesystem")
def ingest_filesystem(req: FilesystemIngestRequest, bg: BackgroundTasks):    
    scope = IndexingScope(
        directories=[Path(p) for p in req.directories],
        recursive=req.recursive,
        include_patterns=req.include_patterns,
        exclude_patterns=req.exclude_patterns,
    )

    run = create_run("filesystem", scope)
    logger.debug(f"Created ingestion run {run.id} for scope: {scope}")
    bg.add_task(ingest_filesystem_scope, scope, run.id, False)

    return {
        "accepted": True,
        "run_id": run.id,
        "status": "running",
    }


