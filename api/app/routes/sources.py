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

