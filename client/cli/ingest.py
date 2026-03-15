import typer 
from pathlib import Path
import httpx
from typing import List
from sources.filesystem import FilesystemIngestionSource, FilesystemIndexingScope
from sources.thunderbird import ThunderbirdIngestionSource, ThunderbirdIndexingScope
from ingest.queue_client import queue_document_part
import logging
logger = logging.getLogger(__name__)

from cli.config import API_URL, BATCH_SIZE

ingest_app = typer.Typer(no_args_is_help=True)

def is_stop_requested(run_id: str) -> bool:
    response = httpx.get(f"{API_URL}/runs/is_stop_requested/{run_id}")
    response.raise_for_status()
    return response.json().get("stop_requested", False)

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
    run_id: str = None,

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

    if not run_id:
        print(f"Connecting to API at: {API_URL}")
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

    else:
        logger.info(f"Using existing run ID {run_id} for filesystem queuing for {path}")
    
    run_is_discovering_response = httpx.get(f"{API_URL}/runs/is_discovering/{run_id}")
    run_is_discovering_response.raise_for_status()
    run_is_discovering = run_is_discovering_response.json().get("is_discovering", False)

    # Start indexing for the run
    indexing_response = httpx.post(
        f"{API_URL}/runs/start_indexing/{run_id}"
    )
    indexing_response.raise_for_status()
    logger.info(f"Started indexing for run {run_id}. Beginning to queue document parts for filesystem at {path} with recursive={recursive}. Status is: {indexing_response.json().get('status')}")

    try: 
        if not run_is_discovering:
            logger.warning(f"Run {run_id} is marked as 'not discovering' at the start of queuing.")
            return

        for doc in source.iter_documents():
            # Check if the run has been requested to stop before processing each document
            # if yes, break out of the loop to stop queuing more document parts
            if is_stop_requested(run_id):
                logger.info(f"Stop requested for run {run_id}. Stopping queuing more document parts for filesystem at {path}.")
                break

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
        if not is_stop_requested(run_id):
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
        
        import traceback
        logger.error(f"Error during filesystem queuing: {e}")
        logger.error(traceback.format_exc())

@ingest_app.command("thunderbird")
def ingest_thunderbird(
        mbox: str = typer.Argument(..., help="Path to Thunderbird mailbox"),
        ignore_from: List[str] = typer.Option([], "--ignore-from"),
):
    queue_thunderbird_logic(mbox=mbox, ignore_from=ignore_from)

def queue_thunderbird_logic(
    mbox: Path = typer.Argument(..., help="Path to Thunderbird mailbox"),
    ignore_from: List[str] = typer.Option([], "--ignore-from"),
    run_id: str = None,
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

    if not run_id:
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
    else:
        logger.info(f"Using existing run ID {run_id} for Thunderbird queuing for {mbox}")

    is_discovering_response = httpx.get(f"{API_URL}/runs/is_discovering/{run_id}")
    is_discovering_response.raise_for_status()
    is_discovering = is_discovering_response.json().get("is_discovering", False)

    # Start indexing for the run
    indexing_response = httpx.post(
        f"{API_URL}/runs/start_indexing/{run_id}"
    )
    indexing_response.raise_for_status()
    logger.info(f"Started indexing for run {run_id}. Beginning to queue document parts for Thunderbird mailbox at {mbox} with ignore_from={ignore_from}. Status is: {indexing_response.json().get('status')}")

    try:
        if not is_discovering:
            logger.warning(f"Run {run_id} is marked as 'not discovering' at the start of queuing.")
            return

        for doc in source.iter_documents():
            # Check if the run has been requested to stop before processing each document
            # if yes, break out of the loop to stop queuing more document parts
            if is_stop_requested(run_id):
                logger.info(f"Stop requested for run {run_id}. Stopping queuing more document parts for Thunderbird mailbox at {mbox}.")
                break

            for part in doc.parts:
                logger.debug(f"Ingesting text: {part.text[:30]}... from email {part.source_path} (Document Part ID: {part.document_part_id})")
                queue_document_part(run_id, part, scope)
                
        # Once all documents are queued, we can mark the run as not discovering anymore
        if not is_stop_requested(run_id):
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

