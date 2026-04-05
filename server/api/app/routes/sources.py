from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from storage.metadata_db.sources import add_monitored_source, get_monitored_source_by_id, update_monitored_source_check_times, list_all_monitored_sources
from loseme_core.models import IndexingScope
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sources", tags=["sources"])

class AddSourceRequest(BaseModel):
    source_type: str
    device_id: str
    scope: dict

@router.post("/add")
async def add_source(request: AddSourceRequest):
    logger.debug(f"Received request to add source of type {request.source_type} with scope {request.scope}")
    scope = IndexingScope.deserialize(request.scope)
    device_id = request.device_id
    source_id = add_monitored_source(request.source_type, device_id, scope)
    logger.info(f"Added monitored source {source_id} of type {request.source_type} with locator {scope.locator}")
    return {"source_id": source_id}

@router.post("/{source_id}/update")
async def update_source(source_id: str, last_seen_fingerprint: str = None, last_checked_at: str = None, last_ingested_at: str = None, enabled: bool = None):
    logger.debug(f"Received request to update source with ID {source_id}")
    update_monitored_source_check_times(
        source_id,
        last_seen_fingerprint=last_seen_fingerprint,
        last_checked_at=last_checked_at,
        last_ingested_at=last_ingested_at,
        enabled=enabled,
    )
    logger.info(f"Updated monitored source with ID {source_id}")
    return {"status": "success"}


@router.get("/get_all_sources")
async def get_all_sources():
    logger.debug("Received request to list all monitored sources")
    sources = list_all_monitored_sources()
    logger.info(f"Retrieved {len(sources)} monitored sources")
    logger.debug(f"Monitored sources: {sources}")
    return {"sources": sources}

@router.get("/get/{source_id}")
async def get_source(source_id: str):
    logger.debug(f"Received request to get source with ID {source_id}")
    source = get_monitored_source_by_id(source_id)
    if not source:
        logger.error(f"Source with ID {source_id} not found")
        raise HTTPException(status_code=404, detail="Source not found")
    logger.info(f"Retrieved source with ID {source_id}")
    return {"source": source}

"""
@router.post("/scan/{source_id}")
async def scan_source(source_id: str, background_tasks: BackgroundTasks):
    from client.cli.sources import scan_source_logic
    from client.cli.ingest import queue_filesystem_logic, queue_thunderbird_logic
    from api.app.routes.runs import create_indexing_run, start_indexing_run
    logger.debug(f"Received request to scan source with ID {source_id}")
     
    # get all sources
    all_sources = await get_all_sources()

    for source in all_sources["sources"]:
        if source["id"] == source_id:
            break

    
    if not source:
        logger.error(f"Source with ID {source_id} not found")
        raise HTTPException(status_code=404, detail="Source not found")

    source_type = source["source_type"]
    if source_type not in ["filesystem", "thunderbird"]:
        logger.error(f"Currently unsupported source type {source_type} for scanning from the API")
        raise HTTPException(status_code=400, detail=f"Currently unsupported source type {source_type} for scanning")

    if source_type == "thunderbird":
        logger.info(f"Scheduling background task to queue the Thunderbird ingestion logic for source ID {source_id}")
        background_tasks.add_task(
            queue_thunderbird_logic,
            mbox=source["scope"].mbox_path,
            ignore_from=[p["value"] for p in source["scope"].ignore_patterns if p["field"] == "from"],
        )

    elif source_type == "filesystem":
        for directory in source["scope"].directories:
            logger.info(f"Scheduling background task to queue the filesystem logic for directory {directory} of source ID {source_id}")

            background_tasks.add_task(
                queue_filesystem_logic,
                path=directory,
                recursive=source["scope"].recursive,
                include_patterns=source["scope"].include_patterns,
                exclude_patterns=source["scope"].exclude_patterns,
            )
        
    return {"status": "scan_started", "source_id": source_id}
"""

from fastapi import HTTPException
from fastapi.responses import JSONResponse

@router.get("/delete/{source_id}")
def delete_source(
    source_id: str,
    dry_run: bool = True,
    confirm: bool = False  # New parameter for confirmation
):
    logger.debug(f"Received request to delete source with ID {source_id}")

    from storage.metadata_db.sources import delete_monitored_source
    from storage.metadata_db.document_parts import delete_all_parts_for_scope


    source = get_monitored_source_by_id(source_id)
    if not source:
        logger.error(f"Source with ID {source_id} not found for deletion")
        raise HTTPException(status_code=404, detail="Source not found")

    if dry_run:
        logger.info(f"Dry run enabled - not actually deleting source with ID {source_id}")
        return {
            "status": "dry_run",
            "source_id": source_id,
            "source_details": source,  # Return source details for confirmation
            "message": "This is a dry run. To proceed with deletion, set `confirm=True`."
        }

    if not confirm:
        return {
            "status": "confirmation_required",
            "source_id": source_id,
            "source_details": source,
            "message": "Deletion is irreversible. Please confirm by setting `confirm=True`."
        }

    # Proceed with deletion
    scope_dict = source["scope"].serialize()
    scope_json = json.dumps(scope_dict)
    logger.debug(f"Deleting all document parts for source ID {source_id} with scope {scope_json} and source type {source['source_type']} from the database and vector store")
    delete_all_parts_for_scope(source["source_type"], scope_json)
    delete_monitored_source(source_id)

    return {"status": "deleted", "source_id": source_id}

class EditSourceRequest(BaseModel):
    source_id: str
    source_type: Optional[str] = None
    locator: Optional[str] = None
    scope_json: Optional[dict] = None
    device_id: Optional[str] = None
    last_seen_fingerprint: Optional[str] = None
    last_checked_at: Optional[str] = None
    last_ingested_at: Optional[str] = None
    enabled: Optional[bool] = None
    created_at: Optional[str] = None


@router.put("/edit/{source_id}")
def edit_source(request: EditSourceRequest):
    from storage.metadata_db.sources import edit_monitored_source
    logger.debug(f"Received request to edit source with ID {request.source_id}")

    source = get_monitored_source_by_id(request.source_id)
    if not source:
        logger.error(f"Source with ID {request.source_id} not found for editing")
        raise HTTPException(status_code=404, detail="Source not found")

    payload = request.dict(exclude_unset=True)
    if "scope_json" in payload and payload["scope_json"] is not None:
        payload["scope_json"] = json.dumps(payload["scope_json"])

    payload.pop("source_id", None)

    edit_monitored_source(request.source_id, **payload)
