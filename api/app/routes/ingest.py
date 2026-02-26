import os
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from pathlib import Path
from typing import Iterable

from src.sources.base.models import Document, Chunk, IngestRequest, DocumentPart
from src.sources.filesystem import FilesystemIngestionSource, FilesystemIngestRequest
from src.sources.thunderbird import ThunderbirdIngestionSource, ThunderbirdIngestRequest
from src.core.ids import make_source_instance_id, make_chunk_id
from storage.metadata_db.indexing_runs import update_status, load_latest_run_by_scope, request_stop, load_latest_run_by_type, load_latest_interrupted, create_run, show_runs, increment_discovered_count, increment_indexed_count
from storage.metadata_db.db import init_db
from storage.metadata_db.document_parts import upsert_document_part, get_document_part_by_id, mark_document_part_processed
from storage.vector_db.runtime import get_vector_store
from src.core.wiring import build_embedding_provider, build_chunker
import logging
import httpx
import os 

API_URL = os.environ.get("LOSEME_API_URL", "http://localhost:8000")

logger = logging.getLogger(__name__)

store = get_vector_store()
chunker = build_chunker()
embedding_provider = build_embedding_provider()

def get_data_root() -> Path:
    return Path(
        os.environ.get("LOSEME_DATA_DIR", "/data")
    ).resolve()

router = APIRouter(prefix="/ingest", tags=["ingestion"])


class IngestDocumentPartRequest(BaseModel):
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
    metadata_json: dict = {}
    created_at: str
    updated_at: str
    text: str
    scope_json: dict

@router.post("/document_part")
def ingest_document_part(req: IngestDocumentPartRequest):
    logger.debug(f"Received ingest request for document part ID {req.document_part_id} in run ID {req.run_id}")
    all_runs = show_runs()
    if req.run_id not in [run.id for run in all_runs]:
        raise HTTPException(status_code=404, detail=f"Run with ID {req.run_id} not found")

    #increment_discovered_count(run_id=req.run_id)
    
    skip_part = False
    old_part = get_document_part_by_id(req.document_part_id)
    
    if old_part:
        logger.debug(f"Document part with ID {req.document_part_id} exists. Comparing extractor_names and versions.")
        skip_part = True
        if old_part["extractor_name"] != req.extractor_name:
            logger.info(f"Extractor name changed from {old_part['extractor_name']} to {req.extractor_name}. Re-processing suggested.")
            skip_part = False
        if old_part["extractor_version"] != req.extractor_version:
            logger.info(f"Extractor version changed from {old_part['extractor_version']} to {req.extractor_version}. Re-processing suggested.")
            skip_part = False
        if old_part.get("checksum") != req.checksum:
            logger.info(f"Checksum changed for document part ID {req.document_part_id}. Re-processing suggested.")
            skip_part = False

    if skip_part:
        logger.info(f"Skipping ingestion for document part ID {req.document_part_id} (already processed).")
        mark_document_part_processed(run_id=req.run_id, document_part_id=req.document_part_id)
        increment_indexed_count(run_id=req.run_id)
        return {
            "accepted": True,
            "skipped": True,
        }

    # Ingest or re-process the part
    try:
        logger.info(f"Ingesting document part ID {req.document_part_id} for run_id {req.run_id}")

        if old_part:
            if old_part["chunk_ids"] is None:
                raise ValueError(f"Existing document part with ID {req.document_part_id} has no chunk_ids. Cannot remove old chunks.")
            else:
                store.remove_chunks(chunk_ids=old_part["chunk_ids"])
        else:
            upsert_document_part(
                part={
                    "document_part_id": req.document_part_id,
                    "checksum": req.checksum,
                    "source_type": req.source_type,
                    "source_instance_id": req.source_instance_id,
                    "device_id": req.device_id,
                    "source_path": req.source_path,
                    "unit_locator": req.unit_locator,
                    "content_type": req.content_type,
                    "extractor_name": req.extractor_name,
                    "extractor_version": req.extractor_version,
                    "metadata_json": req.metadata_json,
                    "created_at": req.created_at,
                    "updated_at": req.updated_at,
                    "text": req.text,
                    "scope_json": req.scope_json,
                },
                run_id=req.run_id,
            )

        part = DocumentPart(
            document_part_id=req.document_part_id,
            checksum=req.checksum,
            source_type=req.source_type,
            source_instance_id=req.source_instance_id,
            device_id=req.device_id,
            source_path=req.source_path,
            unit_locator=req.unit_locator,
            content_type=req.content_type,
            extractor_name=req.extractor_name,
            extractor_version=req.extractor_version,
            metadata_json=req.metadata_json,
            created_at=req.created_at,
            updated_at=req.updated_at,
            text=req.text,
            scope_json=req.scope_json,
        )

        chunks, _ = chunker.chunk(part)
        if chunks is None or len(chunks) == 0:
            logger.warning(f"Chunker returned no chunks for document part ID {req.document_part_id}. Generating a single empty chunk.")

        for chunk in chunks:
            text_to_embed = chunk.text or ""
            if not chunk.text:
                logger.warning(f"Chunk with ID {chunk.id} has no text. Generating empty embedding.")
            embeddings = embedding_provider.embed_document(text_to_embed)

            max_retries = 3

            for attempt in range(1, max_retries + 1):
                try:
                    store.add(chunk, embeddings)
                    break  # Success! Exit the loop
                except Exception as e:
                    if attempt == max_retries:
                        logger.error(f"Failed to add chunk with ID {chunk.id} after {max_retries} attempts: {str(e)}")
                        raise
                    else:
                        logger.warning(f"Error adding chunk with ID {chunk.id} (attempt {attempt}): {str(e)}. Retrying...")


        # Always mark as processed after successful ingestion
        mark_document_part_processed(run_id=req.run_id, document_part_id=req.document_part_id, chunk_ids=[c.id for c in chunks])
        increment_indexed_count(run_id=req.run_id)
        return {
            "accepted": True,
            "skipped": False,
        }

    except Exception as e:
        logger.error(f"Error ingesting document part ID {req.document_part_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ingestion error: {str(e)}")

