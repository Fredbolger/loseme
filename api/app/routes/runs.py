from fastapi import APIRouter, BackgroundTasks
from storage.metadata_db.indexing_runs import create_run, load_latest_run_by_type, request_stop, show_runs, increment_discovered_count, load_latest_interrupted, load_run_by_id, stop_indexing, update_status, stop_discovery, is_stop_requested, set_run_resume
from storage.metadata_db.document_parts_queue import get_next_document_part_from_queue, remove_document_part_from_queue
from storage.metadata_db.document_parts import get_stale_parts, remove_document_parts_by_id
from api.app.routes.ingest import ingest_document_part, IngestDocumentPartRequest
from src.sources.base.models import IndexingScope
import json
import logging
import time
import torch

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/runs", tags=["runs"])

@router.post("/create")
def create_indexing_run(req: dict):
    source_type: str = req["source_type"]
    scope_json: str = req["scope_json"]
    logger.debug(f"Received json scope: {scope_json}")
    if type(scope_json) == str:
        scope_json = json.loads(scope_json)

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
def is_stop_requested_endpoint(run_id: str):
    from storage.metadata_db.indexing_runs import is_stop_requested
    stop_requested = is_stop_requested(run_id)
    return {
        "run_id": run_id,
        "stop_requested": stop_requested,
    }

@router.post("/request_stop/{run_id}")
def request_stop_endpoint(run_id: str):
    request_stop(run_id)
    logger.info(f"Stop requested for indexing run {run_id}")
    return {
        "run_id": run_id,
        "status": "stop_requested",
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

@router.post("/start_indexing/{run_id}")
def start_indexing_run(run_id: str, background_tasks: BackgroundTasks):
    logger.info(f"Starting indexing process for run {run_id}")
    set_run_resume(run_id)
    update_status(run_id, "running")
    # Create a background task to run the indexing process
    background_tasks.add_task(run_indexing_process, run_id)
    
    # Immediately return a response to the client
    return {
        "run_id": run_id,
        "status": "starting",
    }

@router.post("/discovering_stopped/{run_id}")
def mark_discovering_stopped(run_id: str):
    stop_discovery(run_id)

def run_indexing_process(run_id: str):
    logger.info(f"Background indexing process started for run {run_id}")
    processed_count = 0
    while True:
        run = load_run_by_id(run_id)
        if run.stop_requested:
            update_status(run_id, "interrupted")
            logger.info(f"Indexing run {run_id} interrupted by user request.")
            torch.cuda.empty_cache()
            break
       
        logger.debug(f"Checking for next document part in queue for run {run_id}")
        document_part = get_next_document_part_from_queue(run_id)
        if document_part is None:
            logger.debug(f"No document parts in queue for run {run_id}. Checking if run is still discovering.")
            # Check if the run is still discovering documents or if it has completed
            if run.is_discovering == False:
                # If the run is not discovering anymore and there are no document parts in the queue, we can assume the run is completed
                logger.info(f"No more document parts to process and run {run_id} is not discovering anymore. Marking run as completed.")
                cleanup_run(run_id)
                break
            else:
                # If the run is still discovering, wait and check again later
                logger.debug(f"Run {run_id} is still discovering. Waiting for new document parts.")
                time.sleep(0.01)
                continue

        r = ingest_document_part(IngestDocumentPartRequest(
            run_id=run_id,
            document_part_id=document_part["document_part_id"],
            checksum=document_part["checksum"],
            source_type=document_part["source_type"],
            device_id=document_part["device_id"],
            source_path=document_part["source_path"],
            source_instance_id=document_part["source_instance_id"],
            unit_locator=document_part["unit_locator"],
            content_type=document_part["content_type"],
            extractor_name=document_part["extractor_name"],
            extractor_version=document_part["extractor_version"],
            metadata_json=document_part.get("metadata_json", {}),
            created_at=document_part["created_at"],
            updated_at=document_part["updated_at"],
            text=document_part.get("text", ""),
            scope_json=json.loads(document_part.get("scope_json", "{}")),
        ))
        processed_count += 1
        
        if processed_count % 50 == 0:
            torch.cuda.empty_cache()

        if r.get("accepted") == False:
            logger.error(f"Failed to ingest document part {document_part['document_part_id']} in run {run_id}: {r.get('reason', 'Unknown error')}")
        else:
            logger.debug(f"Successfully ingested document part {document_part['document_part_id']} in run {run_id}")
            # Remove the part from the queue after processing
            remove_document_part_from_queue(run_id, document_part["document_part_id"])
        
        del document_part

def cleanup_run(run_id: str):
    stop_indexing(run_id)
    run = load_run_by_id(run_id)
    stale_document_ids, stale_chunk_ids = get_stale_parts(run_id = run_id)
    from storage.vector_db.runtime import get_vector_store
    store = get_vector_store()
    chunk_ids_flattened = [chunk_id for sublist in stale_chunk_ids for chunk_id in sublist]
    if len(chunk_ids_flattened) > 0:
        store.remove_chunks(chunk_ids_flattened)
        remove_document_parts_by_id(stale_document_ids)
    update_status(run_id, "completed")
    torch.cuda.empty_cache()
    logger.info(f"Indexing run {run_id} completed.")

