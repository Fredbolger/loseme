import typer 
from datetime import datetime, timezone
from pathlib import Path
import httpx
import json
from typing import List
from src.sources.base.models import DocumentPart, IndexingScope
from src.sources.filesystem import FilesystemIngestionSource, FilesystemIndexingScope
from src.sources.thunderbird import ThunderbirdIngestionSource, ThunderbirdIndexingScope
import logging
logger = logging.getLogger(__name__)

from clients.cli.config import API_URL, BATCH_SIZE

ingest_app = typer.Typer(no_args_is_help=True)

def is_stop_requested(run_id: str) -> bool:
    response = httpx.get(f"{API_URL}/runs/is_stop_requested/{run_id}")
    response.raise_for_status()
    return response.json().get("stop_requested", False)

def queue_document_part(run_id: str, part: DocumentPart, scope: IndexingScope):
    response = httpx.post(
        f"{API_URL}/queue/add",
        json={
            "part": {
                    "document_part_id": part.document_part_id,
                    "source_type": part.source_type,
                    "checksum": part.checksum,
                    "device_id": part.device_id,
                    "source_path": str(part.source_path),
                    "source_instance_id": part.source_instance_id,
                    "unit_locator": part.unit_locator,
                    "content_type": part.content_type,
                    "extractor_name": part.extractor_name,
                    "extractor_version": part.extractor_version,
                    "metadata_json": part.metadata_json,
                    "created_at": part.created_at.isoformat(),
                    "updated_at": part.updated_at.isoformat(),
                    "text": part.text,
                    "scope_json": scope.serialize(),
            },
            "run_id": run_id,
        },
        timeout=1.0,
    )
    response.raise_for_status()
    logger.info(f"Queued document part with unit_locator {part.unit_locator} and content_type {part.content_type} for file {part.source_path} (Document Part ID: {part.document_part_id})")

@ingest_app.command("filesystem")
def ingest_filesystem(
        path: Path = typer.Argument(..., exists=True, file_okay=False),
        recursive: bool = True,
        include_patterns: List[str] = typer.Option([], "--include-pattern", help="List of glob patterns to include (e.g. --include-pattern *.txt --include-pattern *.md)"),
        exclude_patterns: List[str] = typer.Option([], "--exclude-pattern", help="List of glob patterns to exclude (e.g. --exclude-pattern *.log --exclude-pattern temp/*)"),
):
    queue_filesystem_logic(path=path, recursive=recursive, include_patterns=include_patterns, exclude_patterns=exclude_patterns)

def queue_filesystem_logic(
    path: Path = typer.Argument(..., exists=True, file_okay=False),
    recursive: bool = True,
    include_patterns: List[str] = typer.Option([], "--include-pattern", help="List of glob patterns to include (e.g. --include-pattern *.txt --include-pattern *.md)"),
    exclude_patterns: List[str] = typer.Option([], "--exclude-pattern", help="List of glob patterns to exclude (e.g. --exclude-pattern *.log --exclude-pattern temp/*)"),

):
    """
    Queue a local filesystem directory.
    """
    
    logger.info(f"Starting filesystem queuing for {path}")
    
    # resolve the absolute path to ensure consistency in source_instance_id generation and logging
    if type(path) is str:
        path = Path(path)
    path = path.resolve()

    scope = FilesystemIndexingScope(
        directories=[path],
        recursive=recursive,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
    )

    source = FilesystemIngestionSource(scope, should_stop=lambda: False)
    logger.debug(f"Created FilesystemIngestionSource with scope: {scope}")

    run_response = httpx.post(
        f"{API_URL}/runs/create",
        json={
            "source_type": "filesystem",
            "scope_json": scope.serialize(),
        },
    )
    run_response.raise_for_status()

    run_id = str(run_response.json()["run_id"])
    logger.info(f"Created indexing run with ID: {run_id}")
    
    # Start indexing for the run
    indexing_response = httpx.post(
        f"{API_URL}/runs/start_indexing/{run_id}"
    )
    indexing_response.raise_for_status()
    logger.info(f"Started indexing for run {run_id}. Beginning to queue document parts for filesystem at {path} with recursive={recursive}. Status is: {indexing_response.json().get('status')}")

    try: 
        for doc in source.iter_documents():
            for part in doc.parts:
                try:
                    logger.debug(f"Ingesting text: {part.text[:30]}... from file {part.source_path} (Document Part ID: {part.document_part_id})")
                    queue_document_part(run_id, part, scope)                
                except Exception as e:
                    logger.warning(
                        f"Skipping document part {part.document_part_id} "
                        f"({part.source_path}): {e}"
                    )
        
        # Once all documents are queued, we can mark the run as not discovering anymore
        httpx.post(
            f"{API_URL}/runs/discovering_stopped/{run_id}"
        )
         
        logger.info(f"Completed filesystem queuing for {path}. Marked run {run_id} as discovering stopped.")

    except Exception as e:
        # Request stop
        httpx.post(
            f"{API_URL}/runs/request_stop/{run_id}"
        )
        # and mark run as failed
        httpx.post(
            f"{API_URL}/runs/mark_failed/{run_id}",
            json={"error_message": str(e)},
        )
        

        logger.error(f"Error during filesystem queuing: {e}")

@ingest_app.command("thunderbird")
def ingest_thunderbird(
        mbox: str = typer.Argument(..., help="Path to Thunderbird mailbox"),
        ignore_from: List[str] = typer.Option([], "--ignore-from"),
):
    queue_thunderbird_logic(mbox=mbox, ignore_from=ignore_from)

def queue_thunderbird_logic(
    mbox: Path = typer.Argument(..., help="Path to Thunderbird mailbox"),
    ignore_from: List[str] = typer.Option([], "--ignore-from"),
):
    """
    Queue Thunderbird mailboxes.
    """
    # resolve the absolute path to ensure consistency in source_instance_id generation and logging
    mbox = Path(mbox).resolve()
    mbox = str(mbox)
    logger.info(f"Starting Thunderbird queuing for {mbox}")

    scope = ThunderbirdIndexingScope(
        type="thunderbird",
        mbox_path=mbox,
        ignore_patterns=[{"field": "from", "value": v} for v in ignore_from],
    )

    source = ThunderbirdIngestionSource(scope, should_stop=lambda: False)
    logger.debug(f"Created ThunderbirdIngestionSource with scope: {scope}")

    run_response = httpx.post(
        f"{API_URL}/runs/create",
        json={
            "source_type": "thunderbird",
            "scope_json": scope.serialize(),
        },
    )
    run_response.raise_for_status()
    run_id = str(run_response.json()["run_id"])
    logger.info(f"Created indexing run with ID: {run_id}")

    # Start indexing for the run
    indexing_response = httpx.post(
        f"{API_URL}/runs/start_indexing/{run_id}"
    )
    indexing_response.raise_for_status()
    logger.info(f"Started indexing for run {run_id}. Beginning to queue document parts for Thunderbird mailbox at {mbox} with ignore_from={ignore_from}. Status is: {indexing_response.json().get('status')}")

    try:
        for doc in source.iter_documents():
            for part in doc.parts:
                logger.debug(f"Ingesting text: {part.text[:30]}... from email {part.source_path} (Document Part ID: {part.document_part_id})")
                queue_document_part(run_id, part, scope)
                
        # Once all documents are queued, we can mark the run as not discovering anymore
        httpx.post(
            f"{API_URL}/runs/discovering_stopped/{run_id}"
        )
         
        logger.info(f"Completed Thunderbird queuing for {mbox}. Marked run {run_id} as discovering stopped.")

    except Exception as e:
        # Request stop
        httpx.post(
            f"{API_URL}/runs/request_stop/{run_id}"
        )
        # and mark run as failed
        httpx.post(
            f"{API_URL}/runs/mark_failed/{run_id}",
            json={"error_message": str(e)},
        )

        logger.error(f"Error during Thunderbird queuing: {e}")

