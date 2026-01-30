import os
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from pathlib import Path
from typing import Iterable

from src.domain.models import Document, FilesystemIndexingScope, ThunderbirdIndexingScope, IndexingScope, Chunk
from src.domain.models import  FilesystemIngestRequest, ThunderbirdIngestRequest, GenericIngestRequest
from src.domain.ids import make_source_instance_id, make_chunk_id
from src.core.wiring import build_extractor_registry
from storage.metadata_db.indexing_runs import update_status, update_checkpoint, load_latest_run_by_scope, request_stop, load_latest_run_by_type, load_latest_interrupted, create_run
from storage.metadata_db.processed_documents import mark_processed, is_processed
from storage.metadata_db.document import upsert_document
from storage.metadata_db.db import init_db
from storage.vector_db.runtime import get_vector_store
from src.core.wiring import build_embedding_provider
from api.app.schemas.ingest_documents import IngestDocumentsRequest
from api.app.tasks.ingestion_tasks import ingest_run_task
import logging

logger = logging.getLogger(__name__)

registry = build_extractor_registry()

def get_data_root() -> Path:
    return Path(
        os.environ.get("LOSEME_DATA_DIR", "/data")
    ).resolve()

router = APIRouter(prefix="/ingest", tags=["ingestion"])

@router.post("/documents")
def ingest_documents(req: IngestDocumentsRequest):
    run_id = req.run_id 

    ingest_run_task.delay(run_id = run_id,
                          documents = [d.to_dict() for d in req.documents],
                          )

    return {
        "accepted": True,
        "run_id": run_id,
        "documents": len(req.documents),
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
