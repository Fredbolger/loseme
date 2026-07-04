"""
Paperless-ngx API endpoints for Loseme server.

This module provides endpoints for:
- Managing Paperless connections
- Validating credentials
- Retrieving tags, correspondents, and document types
- Triggering scans
- Proxying document downloads for previews
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Header
from pydantic import BaseModel
from typing import Optional, List
import logging
import os

from storage.metadata_db.paperless_connections import (
    create_paperless_connection,
    get_paperless_connection,
    list_paperless_connections,
    update_paperless_connection,
    delete_paperless_connection,
    validate_paperless_connection,
    get_connection_url_and_token,
)
from storage.metadata_db.sources import add_monitored_source
from api.app.routes.runs import start_indexing_run
from loseme_core.paperless_model import PaperlessIndexingScope
from loseme_core.models import IndexingScope
from paperless_api_client import PaperlessApiClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/paperless", tags=["paperless"])

# Get device ID from environment
device_id = os.environ.get("LOSEME_DEVICE_ID", "server")


# Request/Response Models

class CreateConnectionRequest(BaseModel):
    """Request to create a new Paperless connection."""
    base_url: str
    api_token: str


class UpdateConnectionRequest(BaseModel):
    """Request to update an existing Paperless connection."""
    base_url: Optional[str] = None
    api_token: Optional[str] = None


class ConnectionResponse(BaseModel):
    """Response containing connection information (without credentials)."""
    id: str
    base_url: str
    created_at: str
    updated_at: str


class ValidateConnectionResponse(BaseModel):
    """Response for connection validation."""
    valid: bool
    message: Optional[str] = None


class PaperlessSourceRequest(BaseModel):
    """Request to create a Paperless source."""
    connection_id: str
    tag_ids: Optional[List[int]] = None
    correspondent_ids: Optional[List[int]] = None
    document_type_ids: Optional[List[int]] = None


class PaperlessSourceResponse(BaseModel):
    """Response for creating a Paperless source."""
    source_id: str
    connection_id: str
    filters: dict


class ScanResponse(BaseModel):
    """Response for triggering a Paperless scan."""
    run_id: str
    connection_id: str
    status: str


# Connection Endpoints

@router.post("/connections/create", response_model=ConnectionResponse)
def create_connection(request: CreateConnectionRequest):
    """
    Create a new Paperless-ngx connection.
    
    This stores the connection credentials server-side and returns a connection ID
    that can be used to reference this connection in other endpoints.
    """
    try:
        connection = create_paperless_connection(
            base_url=request.base_url,
            api_token=request.api_token
        )
        
        logger.info(f"Created Paperless connection {connection.id} for {connection.base_url}")
        
        return ConnectionResponse(
            id=connection.id,
            base_url=connection.base_url,
            created_at=connection.created_at,
            updated_at=connection.updated_at
        )
        
    except Exception as e:
        logger.error(f"Error creating Paperless connection: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create connection: {str(e)}")


@router.get("/connections/{connection_id}", response_model=ConnectionResponse)
def get_connection(connection_id: str):
    """
    Get information about a Paperless connection.
    
    Note: This does not return the API token for security.
    """
    connection = get_paperless_connection(connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail=f"Connection with ID {connection_id} not found")
    
    return ConnectionResponse(
        id=connection.id,
        base_url=connection.base_url,
        created_at=connection.created_at,
        updated_at=connection.updated_at
    )


@router.get("/connections", response_model=List[ConnectionResponse])
def list_connections():
    """List all Paperless connections."""
    connections = list_paperless_connections()
    
    return [
        ConnectionResponse(
            id=conn.id,
            base_url=conn.base_url,
            created_at=conn.created_at,
            updated_at=conn.updated_at
        )
        for conn in connections
    ]


@router.put("/connections/{connection_id}", response_model=ConnectionResponse)
def update_connection(connection_id: str, request: UpdateConnectionRequest):
    """Update an existing Paperless connection."""
    connection = update_paperless_connection(
        connection_id=connection_id,
        base_url=request.base_url,
        api_token=request.api_token
    )
    
    if connection is None:
        raise HTTPException(status_code=404, detail=f"Connection with ID {connection_id} not found")
    
    logger.info(f"Updated Paperless connection {connection_id}")
    
    return ConnectionResponse(
        id=connection.id,
        base_url=connection.base_url,
        created_at=connection.created_at,
        updated_at=connection.updated_at
    )


@router.delete("/connections/{connection_id}")
def delete_connection(connection_id: str):
    """Delete a Paperless connection."""
    success = delete_paperless_connection(connection_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Connection with ID {connection_id} not found")
    
    logger.info(f"Deleted Paperless connection {connection_id}")
    return {"status": "success", "message": f"Connection {connection_id} deleted"}


@router.post("/connections/{connection_id}/validate", response_model=ValidateConnectionResponse)
def validate_connection(connection_id: str):
    """
    Validate that a Paperless connection is working.
    
    This tests the API connection and authentication.
    """
    valid = validate_paperless_connection(connection_id)
    
    if valid:
        return ValidateConnectionResponse(valid=True, message="Connection is valid")
    else:
        return ValidateConnectionResponse(valid=False, message="Connection failed")


# Metadata Endpoints

@router.get("/connections/{connection_id}/tags")
def get_tags(connection_id: str):
    """
    Get all tags from a Paperless instance.
    
    This is used to populate the tag filter options when creating a Paperless source.
    """
    connection = get_paperless_connection(connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail=f"Connection with ID {connection_id} not found")
    
    try:
        client = PaperlessApiClient(base_url=connection.base_url, api_token=connection.api_token)
        tags = client.list_all_tags()
        
        logger.debug(f"Retrieved {len(tags)} tags from Paperless connection {connection_id}")
        return {"tags": tags}
        
    except Exception as e:
        logger.error(f"Error fetching tags from Paperless: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch tags: {str(e)}")


@router.get("/connections/{connection_id}/correspondents")
def get_correspondents(connection_id: str):
    """
    Get all correspondents from a Paperless instance.
    
    This is used to populate the correspondent filter options when creating a Paperless source.
    """
    connection = get_paperless_connection(connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail=f"Connection with ID {connection_id} not found")
    
    try:
        client = PaperlessApiClient(base_url=connection.base_url, api_token=connection.api_token)
        correspondents = client.list_all_correspondents()
        
        logger.debug(f"Retrieved {len(correspondents)} correspondents from Paperless connection {connection_id}")
        return {"correspondents": correspondents}
        
    except Exception as e:
        logger.error(f"Error fetching correspondents from Paperless: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch correspondents: {str(e)}")


@router.get("/connections/{connection_id}/document_types")
def get_document_types(connection_id: str):
    """
    Get all document types from a Paperless instance.
    
    This is used to populate the document type filter options when creating a Paperless source.
    """
    connection = get_paperless_connection(connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail=f"Connection with ID {connection_id} not found")
    
    try:
        client = PaperlessApiClient(base_url=connection.base_url, api_token=connection.api_token)
        document_types = client.list_all_document_types()
        
        logger.debug(f"Retrieved {len(document_types)} document types from Paperless connection {connection_id}")
        return {"document_types": document_types}
        
    except Exception as e:
        logger.error(f"Error fetching document types from Paperless: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch document types: {str(e)}")


# Source Management Endpoints

@router.post("/sources/create", response_model=PaperlessSourceResponse)
def create_paperless_source(request: PaperlessSourceRequest):
    """
    Create a new Paperless ingestion source.
    
    This creates a monitored source that will be processed by the ingestion pipeline.
    """
    # Validate the connection exists
    connection = get_paperless_connection(request.connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail=f"Connection with ID {request.connection_id} not found")
    
    # Create the scope
    scope = PaperlessIndexingScope(
        connection_id=request.connection_id,
        tag_ids=request.tag_ids,
        correspondent_ids=request.correspondent_ids,
        document_type_ids=request.document_type_ids
    )
    
    # Add to monitored sources
    source_id = add_monitored_source(
        source_type="paperless",
        device_id=device_id,
        scope=scope
    )
    
    logger.info(f"Created Paperless source {source_id} for connection {request.connection_id}")
    
    return PaperlessSourceResponse(
        source_id=source_id,
        connection_id=request.connection_id,
        filters={
            "tag_ids": request.tag_ids,
            "correspondent_ids": request.correspondent_ids,
            "document_type_ids": request.document_type_ids
        }
    )


# Scan Endpoints

@router.post("/sources/{source_id}/scan", response_model=ScanResponse)
async def trigger_scan(source_id: str, background_tasks: BackgroundTasks, force: bool = False):
    """
    Trigger a scan of a Paperless source.
    
    This runs the ingestion pipeline in the background to index documents from Paperless.
    For server-side sources, this creates a run, discovers documents, and queues them.
    
    Args:
        force: If True, forces re-processing of documents even if they were already processed
    """
    # Import here to avoid circular imports
    from storage.metadata_db.sources import get_monitored_source_by_id
    from storage.metadata_db.indexing_runs import create_run, update_status
    from api.app.routes.runs import start_indexing_run
    from loseme_core.models import IndexingScope
    from paperless_ingestion import PaperlessIngestionSource
    from storage.metadata_db.document_parts_queue import add_document_part_to_queue
    from storage.metadata_db.indexing_runs import increment_discovered_count
    import json
    
    # Get the source
    source = get_monitored_source_by_id(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail=f"Source with ID {source_id} not found")
    
    if source["source_type"] != "paperless":
        raise HTTPException(status_code=400, detail=f"Source {source_id} is not a Paperless source")
    
    # Get the scope from the source
    scope = source.get("scope")
    if scope is None:
        raise HTTPException(status_code=500, detail="Paperless source missing scope")
    
    # Extract connection_id from scope for response
    connection_id = ""
    if hasattr(scope, 'connection_id'):
        connection_id = scope.connection_id
    elif isinstance(scope, dict):
        connection_id = scope.get("connection_id", "")
    
    # Create a new indexing run for this Paperless source
    run = create_run(source_type="paperless", scope=scope)
    run_id = run.id
    
    # Add background task to discover documents and queue them
    background_tasks.add_task(paperless_discovery_task, run_id=run_id, source_id=source_id, scope=scope)
    
    # Start the indexing process for this run
    try:
        start_indexing_run(run_id, background_tasks, force_reprocess=force)
        logger.info(f"Started indexing process for Paperless run {run_id} (force={force})")
    except Exception as e:
        logger.error(f"Failed to start indexing process for run {run_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start indexing: {str(e)}")
    
    logger.info(f"Started Paperless scan for source {source_id}, run ID: {run_id}, force={force}")
    
    return ScanResponse(
        run_id=run_id,
        connection_id=connection_id,
        status="started"
    )


def paperless_discovery_task(run_id: str, source_id: str, scope: IndexingScope):
    """
    Background task to discover Paperless documents and add them to the queue.
    """
    from paperless_ingestion import PaperlessIngestionSource
    from storage.metadata_db.document_parts_queue import add_document_part_to_queue
    from storage.metadata_db.indexing_runs import increment_discovered_count, update_status
    from storage.metadata_db.paperless_connections import get_paperless_connection
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Create the ingestion source
        source = PaperlessIngestionSource(
            scope=scope,
            should_stop=lambda: False,  # For now, no stop mechanism
            update_if_changed_after=None
        )
        
        logger.info(f"Discovering documents for Paperless source {source_id}, run {run_id}")
        
        # Discover documents
        documents = source.iter_documents()
        logger.info(f"Found {len(documents)} documents from Paperless source {source_id}")
        
        # Queue each document part
        queued_count = 0
        for doc in documents:
            for part in doc.parts:
                try:
                    # Serialize scope for storage
                    scope_json = scope.serialize() if hasattr(scope, 'serialize') else {}
                    
                    result = add_document_part_to_queue(
                        part=part.model_dump(),
                        run_id=run_id
                    )
                    
                    if result.get("status") == "already_in_queue":
                        logger.debug(f"Document part {part.document_part_id} already in queue")
                    else:
                        queued_count += 1
                        increment_discovered_count(run_id)
                        logger.debug(f"Queued document part {part.document_part_id}")
                        
                except Exception as e:
                    logger.error(f"Error queuing document part {part.document_part_id}: {str(e)}")
        
        # Mark discovery as complete
        update_status(run_id, "running", is_discovering=False, is_indexing=True)
        logger.info(f"Paperless discovery complete for run {run_id}. Queued {queued_count} document parts.")
        
    except Exception as e:
        logger.error(f"Error in Paperless discovery task for run {run_id}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        update_status(run_id, "failed", is_discovering=False)


# Document Proxy Endpoint

@router.get("/documents/{paperless_document_id}/proxy")
def proxy_document(paperless_document_id: str, connection_id: str):
    """
    Proxy a document from Paperless for preview.
    
    This endpoint allows the client to download the original document file
    without having direct access to the Paperless API token.
    """
    connection = get_paperless_connection(connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail=f"Connection with ID {connection_id} not found")
    
    try:
        client = PaperlessApiClient(base_url=connection.base_url, api_token=connection.api_token)
        
        # Download the document from Paperless
        document_content = client.download_document(int(paperless_document_id))
        
        # Get document metadata to determine content type
        try:
            doc_info = client.get_document(int(paperless_document_id))
            content_type = doc_info.get("mime_type", "application/octet-stream")
            filename = doc_info.get("original_file_name", f"document_{paperless_document_id}")
        except:
            content_type = "application/octet-stream"
            filename = f"document_{paperless_document_id}"
        
        # Return the file with appropriate headers
        from fastapi import Response
        
        logger.debug(f"Proxied document {paperless_document_id} from Paperless connection {connection_id}")
        
        return Response(
            content=document_content,
            media_type=content_type,
            headers={
                "Content-Disposition": f"inline; filename=\"{filename}\"",
                "Content-Type": content_type
            }
        )
        
    except Exception as e:
        logger.error(f"Error proxying document {paperless_document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to proxy document: {str(e)}")


@router.get("/sources/{source_id}/documents")
def list_source_documents(source_id: str):
    """
    List documents from a Paperless source.
    
    This is useful for preview and management purposes.
    """
    from storage.metadata_db.sources import get_monitored_source_by_id
    from loseme_core.paperless_model import PaperlessIndexingScope
    
    # Get the source
    source = get_monitored_source_by_id(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail=f"Source with ID {source_id} not found")
    
    if source["source_type"] != "paperless":
        raise HTTPException(status_code=400, detail=f"Source {source_id} is not a Paperless source")
    
    # Get the scope from the source
    scope = source.get("scope")
    if scope is None:
        raise HTTPException(status_code=500, detail="Paperless source missing scope")
    
    # Extract connection_id and filters from the scope
    if isinstance(scope, dict):
        # If scope is already a dict (from list_all_monitored_sources)
        connection_id = scope.get("connection_id")
        tag_ids = scope.get("tag_ids")
        correspondent_ids = scope.get("correspondent_ids")
        document_type_ids = scope.get("document_type_ids")
    else:
        # If scope is a StoredScope or PaperlessIndexingScope object
        scope_data = scope.serialize() if hasattr(scope, 'serialize') else {}
        connection_id = scope_data.get("connection_id")
        tag_ids = scope_data.get("tag_ids")
        correspondent_ids = scope_data.get("correspondent_ids")
        document_type_ids = scope_data.get("document_type_ids")
    
    if not connection_id:
        raise HTTPException(status_code=500, detail="Paperless source missing connection_id in scope")
    
    connection = get_paperless_connection(connection_id)
    if connection is None:
        raise HTTPException(status_code=404, detail=f"Connection with ID {connection_id} not found")
    
    try:
        client = PaperlessApiClient(base_url=connection.base_url, api_token=connection.api_token)
        
        documents = client.list_all_documents(
            tag_ids=tag_ids,
            correspondent_ids=correspondent_ids,
            document_type_ids=document_type_ids
        )
        
        logger.debug(f"Retrieved {len(documents)} documents from Paperless source {source_id}")
        return {"documents": documents}
        
    except Exception as e:
        logger.error(f"Error fetching documents from Paperless source {source_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch documents: {str(e)}")
