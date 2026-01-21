import os
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from pathlib import Path
from typing import Iterable

from src.domain.models import Document, FilesystemIndexingScope, ThunderbirdIndexingScope, IndexingScope
from src.domain.models import  FilesystemIngestRequest, ThunderbirdIngestRequest, GenericIngestRequest
from src.domain.ids import make_source_instance_id
from src.core.wiring import build_extractor_registry
from storage.metadata_db.indexing_runs import create_run, update_status, update_checkpoint, load_latest_run_by_scope, request_stop, load_latest_run_by_type, load_latest_interrupted
from storage.metadata_db.processed_documents import mark_processed, is_processed
from api.app.services.ingestion import ingest_filesystem_scope, ingest_thunderbird_scope, ingest_scope
from storage.metadata_db.db import init_db
import logging

logger = logging.getLogger(__name__)

registry = build_extractor_registry()

def get_data_root() -> Path:
    return Path(
        os.environ.get("LOSEME_DATA_DIR", "/data")
    ).resolve()

router = APIRouter(prefix="/ingest", tags=["ingestion"])

"""
@router.post("/filesystem")
def ingest_filesystem(req: FilesystemIngestRequest, bg: BackgroundTasks):    
    scope = FilesystemIndexingScope(
        type="filesystem",
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

@router.post("/thunderbird")
def ingest_thunderbird(req: ThunderbirdIngestRequest, bg: BackgroundTasks):
    scope = ThunderbirdIndexingScope(
        type="thunderbird",
        mbox_path=req.mbox_path,
        ignore_patterns=req.ignore_patterns,
    )

    run = create_run("thunderbird", scope)
    logger.debug(f"Created ingestion run {run.id} for scope: {scope}")
    bg.add_task(ingest_thunderbird_scope, scope, run.id, False)

    return {
        "accepted": True,
        "run_id": run.id,
        "status": "running",
    }
"""

@router.post("/")
def ingest_source(req_data: GenericIngestRequest, bg: BackgroundTasks):
    # protect reserved keys
    RESERVED_KEYS = {"type"}
    
    try:
        if RESERVED_KEYS.intersection(req_data.data.keys()):
            raise ValueError(f"Request data contains reserved keys: {RESERVED_KEYS.intersection(req_data.data.keys())}")

        logger.debug(f"Deserializing indexing scope from request data: {req_data}")
        data_dict = {
            "type": req_data.type,
            **req_data.data
        }
        scope = IndexingScope.deserialize(data_dict)
    except ValueError as e:
        logger.error(f"Error deserializing indexing scope: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    run = create_run(scope.type, scope)
    logger.debug(f"Created ingestion run {run.id} for scope: {scope}") 
    bg.add_task(ingest_scope, scope, run.id, False)
  
    return {
        "accepted": True,
        "run_id": run.id,
        "status": "running",
    }

@router.post("/stop_latest/{source_type}")
def stop_latest_ingestion_run(source_type: str):
    run = load_latest_run_by_type(source_type)
    if not run:
        raise HTTPException(status_code=404, detail="No active ingestion run found")

    request_stop(run.id)
    logger.info(f"Stop requested for ingestion run {run.id} of type {source_type}")

    return {
        "run_id": run.id,
        "status": "stop_requested",
    }

@router.post("/resume_latest/{source_type}")
def resume_latest_ingestion_run(source_type: str, bg: BackgroundTasks):
    run = load_latest_interrupted(source_type)
    
    if not run:
        raise HTTPException(status_code=404, detail="No interrupted ingestion run found")
    logger.info(f"Resuming ingestion run {run.id} of type {source_type}")

    scope = run.scope
    
    try:
        bg.add_task(ingest_scope, scope, run.id, True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "run_id": run.id,
        "status": "resuming",
    }
