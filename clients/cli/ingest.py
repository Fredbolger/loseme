import typer 
import asyncio
from pathlib import Path
import httpx
from typing import List
from collectors.filesystem.filesystem_source import FilesystemIngestionSource
from collectors.thunderbird.thunderbird_source import ThunderbirdIngestionSource
from src.domain.models import FilesystemIndexingScope, ThunderbirdIndexingScope
import logging
logger = logging.getLogger(__name__)

from clients.cli.config import API_URL, BATCH_SIZE

ingest_app = typer.Typer(no_args_is_help=True)

def is_stop_requested(run_id: str) -> bool:
    response = httpx.get(f"{API_URL}/runs/is_stop_requested/{run_id}")
    response.raise_for_status()
    return response.json().get("stop_requested", False)

def add_discovered_document_to_db(run_id: str, source_instance_id: str, content_checksum: str) -> None:
    response = httpx.post(
        f"{API_URL}/documents/add_discovered_document",
        json={
            "run_id": run_id,
            "source_instance_id": source_instance_id,
            "content_checksum": content_checksum,
        },
    )
    response.raise_for_status()
    logger.debug(
        f"Marked document with source_instance_id {source_instance_id} "
        f"and checksum {content_checksum} as discovered for run {run_id}"
    )

def _send_batch(run_id: str, batch: list[dict]) -> None:
    logger.debug(
        f"Sending batch with {len(batch)} documents for run {run_id}"
    )

    r = httpx.post(
        f"{API_URL}/ingest/documents",
        json={
            "run_id": run_id,
            "documents": batch,
        },
        timeout=120.0,
    )
    r.raise_for_status()

async def _send_batch_async(run_id: str, batch: list[dict]) -> None:
    logger.debug(
        f"Sending batch with {len(batch)} documents for run {run_id}"
    )

    async with httpx.AsyncClient(timeout=300.0) as client:
        r = await client.post(
            f"{API_URL}/ingest/documents",
            json={
                "run_id": run_id,
                "documents": batch,
            },
        )
        r.raise_for_status()

@ingest_app.command("filesystem")
async def ingest_filesystem(
    path: Path = typer.Argument(..., exists=True, file_okay=False),
    recursive: bool = True,
):
    """
    Ingest a local filesystem directory.
    Extraction + chunking happens locally.
    Embedding + storage happens in the backend.
    """
    
    BATCH_SIZE = 5 

    logger.info(f"Starting filesystem ingestion for {path}")

    scope = FilesystemIndexingScope(
        directories=[path],
        recursive=recursive,
        include_patterns=[],
        exclude_patterns=[],
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

    documents_batch: list[dict] = []
    sent_any = False

    for doc in source.iter_documents():
        if is_stop_requested(run_id):
            logger.info("Stop requested, terminating filesystem ingestion.")
            break

        # Increment discovered document count runs/increment_discovered/{run_id}
        response = httpx.post(
            f"{API_URL}/runs/increment_discovered/{run_id}/{doc.id}"
        )
        # Add the discovered document to the database
        add_discovered_document_to_db(
            run_id=run_id,
            source_instance_id=doc.source_id,
            content_checksum=doc.checksum,
        )

        logger.info(
            f"Processing document {doc.source_path} (ID: {doc.id}) "
            f"with size {len(doc.text)} characters"
        )

        documents_batch.append(
            {
                "id": doc.id,
                "source_type": doc.source_type,
                "source_id": doc.source_id,
                "device_id": doc.device_id,
                "source_path": str(doc.source_path),
                "checksum": doc.checksum,
                "created_at": doc.created_at.isoformat(),
                "updated_at": doc.updated_at.isoformat(),
                "metadata": doc.metadata,
                "text": doc.text,
            }
        )

        if len(documents_batch) >= BATCH_SIZE:
            #_send_batch(run_id, documents_batch)
            await _send_batch_async(run_id, documents_batch)
            documents_batch.clear()
            sent_any = True

    if documents_batch:
        # _send_batch(run_id, documents_batch)
        await _send_batch_async(run_id, documents_batch)
        sent_any = True

    if not sent_any:
        typer.echo("No documents found.")
        raise typer.Exit(code=0)

    typer.echo("Filesystem ingestion completed successfully.")

@ingest_app.command("thunderbird")
def ingest_thunderbird(
    mbox: str = typer.Argument(..., help="Path to Thunderbird mailbox"),
    ignore_from: List[str] = typer.Option([], "--ignore-from"),
):
    """
    Ingest Thunderbird mailboxes.
    Extraction + chunking happens locally.
    Embedding + storage happens in the backend.
    """
    mbox = str(mbox)
    logger.info(f"Starting Thunderbird ingestion for {mbox}")

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
    documents_batch: list[dict] = []
    sent_any = False
    
    try:
        for doc in source.iter_documents():
            if is_stop_requested(run_id):
                logger.info("Stop requested, terminating Thunderbird ingestion.")
                raise RuntimeError("Ingestion stopped by user request.") 
            # Increment discovered document count runs/increment_discovered/{run_id}
            response = httpx.post(
                f"{API_URL}/runs/increment_discovered/{run_id}"
            )
            # Add the discovered document to the database
            add_discovered_document_to_db(
                run_id=run_id,
                source_instance_id=doc.source_id,
                content_checksum=doc.checksum,
            )

            logger.info(
                f"Processing email {doc.source_path} (ID: {doc.id}) "
                f"with size {len(doc.text)} characters"
            )

            documents_batch.append(
                {
                    "id": doc.id,
                    "source_type": doc.source_type,
                    "source_id": doc.source_id,
                    "device_id": doc.device_id,
                    "source_path": str(doc.source_path),
                    "checksum": doc.checksum,
                    "created_at": doc.created_at.isoformat(),
                    "updated_at": doc.updated_at.isoformat(),
                    "metadata": doc.metadata,
                    "text": doc.text,
                }
            )

            if len(documents_batch) >= BATCH_SIZE:
                _send_batch(run_id, documents_batch)
                documents_batch.clear()
                sent_any = True

        if documents_batch:
            _send_batch(run_id, documents_batch)
            sent_any = True

        if not sent_any:
            typer.echo("No documents found.")
            return
    
    except Exception as e:
        logger.error(f"Error during Thunderbird ingestion: {e}")
        if isinstance(e, RuntimeError) and str(e) == "Ingestion stopped by user request.":
            typer.echo("Thunderbird ingestion was stopped by user request.")
            httpx.post(
                f"{API_URL}/runs/mark_interrupted/{run_id}"
            )
        else:
            httpx.post(
                f"{API_URL}/runs/mark_failed/{run_id}",
                json={"error_message": str(e)},
            )

    else:
        mark_completed_response = httpx.post(
            f"{API_URL}/runs/mark_completed/{run_id}"
        )
        typer.echo("Thunderbird ingestion completed successfully.")

