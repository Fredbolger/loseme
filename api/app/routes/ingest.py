import os
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from pathlib import Path
from typing import Iterable

from src.sources.base.models import Document, Chunk, IngestRequest
from src.sources.base import extractor_registry
from src.sources.filesystem import FilesystemIngestionSource, FilesystemIngestRequest
from src.sources.thunderbird import ThunderbirdIngestionSource, ThunderbirdIngestRequest
from src.core.ids import make_source_instance_id, make_chunk_id
from storage.metadata_db.indexing_runs import update_status, update_checkpoint, load_latest_run_by_scope, request_stop, load_latest_run_by_type, load_latest_interrupted, create_run
from storage.metadata_db.db import init_db
from storage.vector_db.runtime import get_vector_store
from src.core.wiring import build_embedding_provider
from api.app.schemas.ingest_documents import IngestDocumentsRequest
from api.app.tasks.ingestion_tasks import ingest_run_task
import logging

logger = logging.getLogger(__name__)

registry = extractor_registry

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

