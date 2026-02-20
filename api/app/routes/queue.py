from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.sources.base.models import DocumentPart
from typing import Optional
import logging

logger = logging.getLogger(__name__)

from storage.metadata_db.document_parts_queue import add_document_part_to_queue, get_next_document_part_from_queue, get_all_document_parts_in_queue_for_run, clear_queue_for_run, get_all_document_parts_in_queue, clear_all_queues

router = APIRouter(prefix="/queue", tags=["queue"])

class QueueAddRequest(BaseModel):
    part: DocumentPart
    run_id: str

class QueueGetResponse(BaseModel):
    run_id: str
    document_part_id: str
    checksum: str
    source_type: str
    source_instance_id: str
    device_id: str
    source_path: str
    metadata_json: Optional[dict] = {}
    unit_locator: str
    content_type: str
    extractor_name: str
    extractor_version: str
    created_at: str
    updated_at: str
    text: Optional[str] = None
    scope_json: Optional[dict] = None

@router.post("/add")
def add_to_queue(request: QueueAddRequest):
    try:
        add_document_part_to_queue(part=request.part.model_dump(), run_id=request.run_id)
        logger.debug(f"Document part {request.part.document_part_id} added to queue successfully")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/next/{run_id}", response_model=QueueGetResponse)
def get_next_from_queue(run_id: str):
    try:
        part = get_next_document_part_from_queue(run_id)
        if part:
            return QueueGetResponse(**part)
        else:
            raise HTTPException(status_code=404, detail="No document parts in queue for this run_id")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/show_all_queues")
def show_all_queues():
    try:
        document_parts = get_all_document_parts_in_queue()
        logger.debug(f"Fetched {len(document_parts)} total document parts in queue across all run_ids")
        return {"total_parts": len(document_parts)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/show_all/{run_id}")
def show_all_in_queue(run_id: str):
    try:
        parts = get_all_document_parts_in_queue_for_run(run_id)
        logger.debug(f"Fetched {len(parts)} document parts in queue for run_id {run_id}")
        return {"total_parts": len(parts)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/clear/{run_id}")
def clear_queue(run_id: str):
    try:
        document_parts = get_all_document_parts_in_queue(run_id)
        count = len(document_parts)
        clear_queue_for_run(run_id)
        logger.debug(f"Cleared queue for run_id {run_id}")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/clear_all")
def clear_all_queues_endpoint():
    try:
        clear_all_queues()
        logger.debug("Cleared all queues for all run_ids")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
