from fastapi import APIRouter
from storage.metadata_db.indexing_runs import create_run, load_latest_run_by_type, request_stop, show_runs, increment_discovered_count, load_latest_interrupted
from src.sources.base.models import IndexingScope
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

@router.get("/is_stop_requested/{run_id}")
def is_stop_requested(run_id: str):
    from storage.metadata_db.indexing_runs import is_stop_requested
    stop_requested = is_stop_requested(run_id)
    return {
        "run_id": run_id,
        "stop_requested": stop_requested,
    }

@router.get("/resume_latest/{source_type}")
def load_latest_indexing_run(source_type: str):
    run = load_latest_interrupted(source_type)
    scope = run.scope

    if not run:
        return {
            "error": "No interrupted indexing run found",
            "run_id": None,
        }

    return {
        "run_id": run.id,
        "status": run.status,
        "started_at": run.start_time.isoformat(),
        "mbox_path": scope.mbox_path if hasattr(scope, 'mbox_path') else None,
        "ignore_patterns": scope.ignore_patterns if hasattr(scope, 'ignore_patterns') else None,
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

@router.post("/increment_discovered/{run_id}")
def increment_discovered_documents(run_id: str):
    increment_discovered_count(run_id)
    logger.debug(f"Incremented discovered document count for run {run_id}")
    return {"run_id": run_id, "status": "incremented"}

@router.post("/mark_completed/{run_id}")
def mark_run_finished(run_id: str):
    from storage.metadata_db.indexing_runs import update_status
    update_status(run_id, "completed")
    logger.info(f"Marked run {run_id} as completed")
    return {"run_id": run_id, "status": "completed"}

@router.post("/mark_failed/{run_id}")
def mark_run_failed(run_id: str):
    from storage.metadata_db.indexing_runs import update_status
    update_status(run_id, "failed")
    logger.info(f"Marked run {run_id} as failed")
    return {"run_id": run_id, "status": "failed"}

@router.post("/mark_interrupted/{run_id}")
def mark_run_interrupted(run_id: str):
    from storage.metadata_db.indexing_runs import update_status
    update_status(run_id, "interrupted")
    logger.info(f"Marked run {run_id} as interrupted")
    return {"run_id": run_id, "status": "interrupted"}
