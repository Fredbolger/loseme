from fastapi import APIRouter
from storage.metadata_db.indexing_runs import create_run, load_latest_run_by_type, request_stop, show_runs
from src.domain.models import IndexingScope
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/runs", tags=["runs"])

@router.post("/create")
def create_indexing_run(req: dict):
    source_type: str = req["source_type"]
    scope_json: str = req["scope_json"]
    logger.debug(f"Received json scope: {scope_json}")
    scope = IndexingScope.deserialize(scope_json)
    
    logger.debug(f"Deserialized scope: {scope}")

    run = create_run(source_type=source_type, scope=scope)
    return {
        "run_id": run.id,
        "status": run.status,
        "started_at": run.start_time.isoformat(),
    }

@router.post("/stop_latest/{source_type}")
def stop_latest_indexing_run(source_type: str):
    run = load_latest_run_by_type(source_type)
    if not run:
        return {
            "error": "No active indexing run found",
            "run_id": None,
        }

    request_stop(run.id)
    logger.info(f"Stop requested for indexing run {run.id} of type {source_type}")

    return {
        "run_id": run.id,
        "status": "stop_requested",
    }

@router.get("/list")
def list_indexing_runs():
    runs = show_runs()
    return {
        "runs": [
            {
                "run_id": r.id,
                "source_type": r.scope.type,
                "status": r.status,
                "started_at": r.start_time.isoformat(),
                "updated_at": r.updated_at.isoformat(),
                "discovered_document_count": r.discovered_document_count,
                "indexed_document_count": r.indexed_document_count,
            }
            for r in runs
        ]
    }

