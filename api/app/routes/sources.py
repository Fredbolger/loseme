from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from storage.metadata_db.monitor_sources import add_monitored_source, get_monitored_source_by_id, update_monitored_source_check_times, list_all_monitored_sources
from storage.metadata_db.indexing_runs import create_run, update_status, increment_discovered_count, stop_discovery
from src.sources.base.models import IndexingScope
from src.sources.filesystem import FilesystemIngestionSource
from src.sources.thunderbird import ThunderbirdIngestionSource
import json
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sources", tags=["sources"])

class AddSourceRequest(BaseModel):
    source_type: str
    scope: dict

@router.post("/add")
async def add_source(request: AddSourceRequest):
    logger.debug(f"Received request to add source of type {request.source_type} with scope {request.scope}")
    scope = IndexingScope.deserialize(request.scope)
    source_id = add_monitored_source(request.source_type, scope)
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
    return {"sources": sources}

@router.post("/scan/{source_id}")
async def scan_source(source_id: str, background_tasks: BackgroundTasks):
    from clients.cli.sources import scan_source_logic
    from clients.cli.ingest import queue_filesystem_logic 
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
    if source_type != "filesystem":
        logger.error(f"Currently unsupported source type {source_type} for scanning from the API")
        raise HTTPException(status_code=400, detail=f"Currently unsupported source type {source_type} for scanning")

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
