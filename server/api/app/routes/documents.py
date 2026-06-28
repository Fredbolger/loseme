from pydantic import BaseModel
from fastapi import HTTPException, APIRouter, BackgroundTasks
from storage.metadata_db.document_parts import (upsert_document_part,
retrieve_scope_by_document_part_id, get_document_part_by_id,
get_document_stats)
from preview import preview_registry
from storage.metadata_db.indexing_runs import increment_discovered_count

from loseme_core.models import IngestionSource
from typing import Optional
import json
import logging
import os
import traceback
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

class AddDiscoveredDocumentPartRequest(BaseModel):
    run_id: str
    document_part_id: str
    source_type: str
    checksum: str
    device_id: str
    source_path: str
    source_instance_id: str
    unit_locator: str 
    content_type: str
    extractor_name: str
    extractor_version: str
    metadata_json: Optional[dict] = {}
    created_at: str
    updated_at: str
    scope_json: Optional[dict] = None

class DocumentPartResponse(BaseModel):
    document_part_id: Optional[str] = None
    source_instance_id: Optional[str] = None
    part: dict

class BatchGetRequest(BaseModel):
    document_part_ids: list[str]

class DocumentStatResponse(BaseModel):
    total_document_parts: int
    total_sources: int
    total_devices: int

@router.post("/add_discovered_document_part")
def add_discovered_document_part_endpoint(req: AddDiscoveredDocumentPartRequest):
    """
    Mark a document as discovered but not yet indexed.

    Args:
        run_id: The ID of the indexing run.
        source_instance_id: The source instance ID of the document.
        content_checksum: The checksum of the document content.

    Returns:
        Success message.
    """
    upsert_document_part(
        part={
            "document_part_id": req.document_part_id,
            "checksum": req.checksum,
            "source_type": req.source_type,
            "source_instance_id": req.source_instance_id,
            "device_id": req.device_id,
            "source_path": req.source_path,
            "metadata_json": req.metadata_json,
            "unit_locator": req.unit_locator,
            "content_type": req.content_type,
            "extractor_name": req.extractor_name,
            "extractor_version": req.extractor_version,
            "created_at": req.created_at,
            "updated_at": req.updated_at,
            "scope_json": req.scope_json
        },
        run_id=req.run_id
    )

    increment_discovered_count(req.run_id)

    return {"status": "Document part marked as discovered."}


@router.get("/open/{document_part_id}")
def get_open_descriptor(document_part_id: str):
    doc_part = get_document_part_by_id(document_part_id)
    if doc_part is None:
        raise HTTPException(404, "Document not found")

    source_type, scope = retrieve_scope_by_document_part_id(document_part_id)
    source = IngestionSource.from_scope(scope, should_stop=lambda: False)

    return source.get_open_descriptor(doc_part)

@router.post("/batch_get")
def batch_get_document_parts(req: BatchGetRequest):
    """
    Retrieve multiple document parts by their IDs.

    Args:
        document_part_ids: List of document part IDs to retrieve.

    Returns:
        List of document metadata.
    """
    documents_parts = []
    for doc_part_id in req.document_part_ids:
        document_part = get_document_part_by_id(doc_part_id)
        if document_part:
            documents_parts.append(document_part)
    return {"documents_parts": documents_parts}


@router.get("/get_all_document_parts", response_model=list[DocumentPartResponse])
def get_all_document_parts_endpoint() -> list[DocumentPartResponse]:
    """
    Retrieve all document parts in the system.
    Returns:
        List of all document parts.
    """
    from storage.metadata_db.document_parts import get_all_document_part_ids

    document_part_ids = get_all_document_part_ids()
    document_parts = []
    for doc_part_id in document_part_ids:
        if doc_part_id is None:
            logger.warning(f"Document part with ID {doc_part_id} is None. Skipping.")
            continue
        document_part = get_document_part_by_id(doc_part_id)
        if document_part is None:
            logger.warning(f"Document part with ID {doc_part_id} not found. Skipping.")
            continue
        document_parts.append(DocumentPartResponse(document_part_id=doc_part_id, source_instance_id=document_part.get("source_instance_id"), part=document_part))

    return document_parts

@router.get("/stats", response_model=DocumentStatResponse)
def get_document_stats_endpoint() -> DocumentStatResponse:
    """
    Retrieve statistics about documents in the system.

    Returns:
        A dictionary containing document statistics.
    """
    
    stats = get_document_stats()
    logger.debug(f"Document stats retrieved: {stats}")
    return DocumentStatResponse(
        total_document_parts=stats.get("total_document_parts", 0),
        total_sources=stats.get("total_sources", 0),
        total_devices=stats.get("total_devices", 0)
    )


@router.get("/stats/per_source")
def get_document_stats_per_source_endpoint():
    """
    Retrieve statistics about documents grouped by source instance ID.

    Returns:
        A list of dictionaries containing document statistics per source instance ID.
    """
    from storage.metadata_db.document_parts import get_document_stats_per_source

    stats_per_source = get_document_stats_per_source()
    logger.debug(f"Document stats per source retrieved: {stats_per_source}")
    return {"stats_per_source": stats_per_source}


@router.get("/stats/chunker")
def get_chunker_stats():
    from storage.metadata_db.document_parts import get_chunker_stats
    return {"stats": get_chunker_stats()}


@router.get("/scope/{document_part_id}")
def get_scope(document_part_id: str):
    result = retrieve_scope_by_document_part_id(document_part_id)
    if result is None:
        raise HTTPException(404, "Scope not found")
    source_type, scope = result
    return {"source_type": source_type}

@router.get("/preview/{document_part_id}")
def preview_document(document_part_id: str):
    logger.debug(f"Preview request received for document_part_id: {document_part_id}")
    doc_part = get_document_part_by_id(document_part_id)
    if doc_part is None:
        raise HTTPException(404, "Document not found")

    source_type, _ = retrieve_scope_by_document_part_id(document_part_id)

    generator = preview_registry.get_generator(source_type, doc_part)
    if generator is None:
        raise HTTPException(400, f"Preview not supported for source_type='{source_type}', "
                                 f"path='{doc_part.get('source_path')}'")

    return generator.generate(doc_part).to_dict()

@router.get("/by_id/{document_id}")
def get_document_by_id_route(document_id: str):
    doc = get_document_part_by_id(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.get("/by_source/{source_id}")
def get_documents_by_source(source_id: str):
    """Get all document parts for a given source ID."""
    from storage.metadata_db.document_parts import get_document_parts_by_source_id
    documents = get_document_parts_by_source_id(source_id)
    return {"documents": documents}


@router.get("/{document_part_id}")
def get_document_part(document_part_id: str):
    """
    Retrieve document metadata by document ID.

    Args:
        document_part_id: The ID of the document part to retrieve.

    Returns:
        Document metadata if found.

    Raises:
        HTTPException: If the document is not found.
    """
    document_part = get_document_part_by_id(document_part_id)
    
    if not document_part:
        logger.warning(f"Document part with ID {document_part_id} not found.")
        raise HTTPException(status_code=404, detail=f"Document with ID {document_part_id} not found.")
    
    return {"document_part": document_part}

@router.get("/{document_part_id}/chunks")
def get_document_chunks(document_part_id: str):
    """Get all chunks for a document part."""
    doc_part = get_document_part_by_id(document_part_id)
    if not doc_part:
        raise HTTPException(404, "Document not found")
    
    chunk_ids = doc_part.get("chunk_ids")
    if not chunk_ids:
        return {"chunks": []}
    
    chunk_ids = json.loads(chunk_ids) if isinstance(chunk_ids, str) else chunk_ids
    
    from storage.vector_db.runtime import get_vector_store
    store = get_vector_store()
    chunks = []
    for chunk_id in chunk_ids:
        chunk = store.retrieve_chunk_by_id(chunk_id)
        if chunk:
            chunks.append(chunk)
    
    return {"chunks": chunks}

@router.get("/{document_part_id}/attachments")
def get_document_attachments(document_part_id: str):
    """Get attachments for a document."""
    doc_part = get_document_part_by_id(document_part_id)
    if not doc_part:
        raise HTTPException(404, "Document not found")
    
    # This depends on your attachment storage model
    # For now, return metadata about attachments from the document part
    metadata = doc_part.get("metadata_json", {})
    attachments = metadata.get("attachments", [])
    return {"attachments": attachments}


@router.post("/{document_part_id}/rescan")
def rescan_document(document_part_id: str):
    """
    Re-scan a document to check if it can still be retrieved and reindex it.

    Args:
        document_part_id: The ID of the document part to re-scan.

    Returns:
        Success message with reindexing status.

    Process:
        1. Retrieve document metadata
        2. Attempt to re-open the source
        3. Extract content if possible
        4. Add to queue for reindexing (if content extracted)
        5. Ensure the run is active for processing
        6. Return status
    """
    try:
        # Step 1: Retrieve document metadata
        document_part = get_document_part_by_id(document_part_id)
        if not document_part:
            raise HTTPException(status_code=404, detail=f"Document with ID {document_part_id} not found.")

        # Step 2: Request content extraction from client
        try:
            # Call the client to extract document content
            client_url = os.environ.get("LOSEME_CLIENT_URL", "http://loseme-client-1:3000")
            client_endpoint = f"{client_url}/preview/{document_part_id}/content"
            
            logger.info(f"Requesting content extraction from client: {client_endpoint}")
            
            import httpx
            import traceback
            client_response = httpx.get(client_endpoint, timeout=30.0)
            
            if client_response.status_code != 200:
                logger.warning(f"Client content extraction failed for document {document_part_id}: {client_response.text}")
                return {"status": "error", "reason": "client_extraction_failed", "document_part_id": document_part_id, "client_error": client_response.text}
                
            logger.info(f"About to parse JSON response")
            extraction_result = client_response.json()
            logger.info(f"Successfully parsed JSON: {extraction_result}")
            
            # Debug: Check if the document_part has datetime fields
            logger.debug(f"Before processing - document_part created_at: {document_part.get('created_at')} (type: {type(document_part.get('created_at'))})")
            logger.debug(f"Before processing - document_part updated_at: {document_part.get('updated_at')} (type: {type(document_part.get('updated_at'))})")
            
            if extraction_result.get("status") != "success":
                logger.warning(f"Client content extraction returned error for document {document_part_id}: {extraction_result}")
                return {"status": "error", "reason": "client_extraction_error", "document_part_id": document_part_id, "client_response": extraction_result}
                
            content = extraction_result.get("content", "")
            
            if not content or not content.strip():
                logger.warning(f"Cannot re-scan document {document_part_id}: No content extracted by client")
                return {"status": "error", "reason": "no_content_extracted", "document_part_id": document_part_id}
                
            # Step 3: Prepare document for reindexing
            document_part["text"] = content
            document_part["updated_at"] = datetime.now()  # Keep as datetime object for queue processing
            
            # Debug: Check types of datetime fields
            logger.debug(f"Document part created_at type: {type(document_part.get('created_at'))}")
            logger.debug(f"Document part updated_at type: {type(document_part.get('updated_at'))}")
            
            # Find existing run or use a default one
            run_id = document_part.get("run_id")
            if not run_id:
                # If no run_id, we need to find or create one
                # For now, let's use a default reindexing run
                run_id = "reindexing_run"

            # Add to queue for reindexing
            logger.info(f"ABOUT TO CALL QUEUE FUNCTION - created_at: {document_part.get('created_at')} (type: {type(document_part.get('created_at'))}), updated_at: {document_part.get('updated_at')} (type: {type(document_part.get('updated_at'))})")
            
            from storage.metadata_db.document_parts_queue import add_document_part_to_queue
            logger.info(f"ABOUT TO CALL add_document_part_to_queue")
            queue_result = add_document_part_to_queue(
                part=document_part,
                run_id=run_id
            )
            logger.info(f"QUEUE FUNCTION RETURNED: {queue_result}")

            if queue_result.get("status") == "already_in_queue":
                logger.info(f"Document {document_part_id} already in queue for reindexing")
                return {"status": "already_in_queue", "document_part_id": document_part_id, "run_id": run_id}
            else:
                logger.info(f"Document {document_part_id} added to queue for reindexing")
                
                # Ensure the run is active for processing
                # If this is a new reindexing run, we need to start it
                if run_id == "reindexing_run":
                    from fastapi import BackgroundTasks
                    from .runs import start_indexing_run
                    
                    # Create a mock background tasks object
                    background_tasks = BackgroundTasks()
                    
                    # Start the indexing process for this run
                    try:
                        start_indexing_run(run_id, background_tasks, force_reprocess=True)
                        logger.info(f"Started indexing process for reindexing run {run_id}")
                    except Exception as e:
                        logger.error(f"Failed to start indexing process for run {run_id}: {str(e)}")
                        return {"status": "error", "reason": "indexing_start_failed", "error": str(e), "document_part_id": document_part_id}

                return {"status": "queued_and_processing", "document_part_id": document_part_id, "run_id": run_id}

        except Exception as extract_error:
            logger.error(f"Error extracting content for document {document_part_id}: {str(extract_error)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {"status": "error", "reason": "extraction_failed", "error": str(extract_error), "document_part_id": document_part_id}

    except Exception as source_error:
        logger.error(f"Error re-opening source for document {document_part_id}: {str(source_error)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return {"status": "error", "reason": "source_error", "error": str(source_error), "document_part_id": document_part_id}
