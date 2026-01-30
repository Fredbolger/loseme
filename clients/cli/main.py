import os
import typer
import httpx
import logging
from pathlib import Path
from typing import List, Dict, Any

from collectors.filesystem.filesystem_source import FilesystemIngestionSource
from collectors.thunderbird.thunderbird_source import ThunderbirdIngestionSource
from storage.metadata_db.indexing_runs import create_run
from src.domain.models import FilesystemIndexingScope, ThunderbirdIndexingScope
from src.core.wiring import build_chunker

app = typer.Typer(no_args_is_help=True)
ingest = typer.Typer(no_args_is_help=True)
app.add_typer(ingest, name="ingest")
run = typer.Typer(no_args_is_help=True)
app.add_typer(run, name="run")

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

API_URL = os.environ.get("API_URL", "http://localhost:8000")
DEVICE_ID = os.environ.get("LOSEME_DEVICE_ID", "unknown-device")

BATCH_SIZE = 20  # tune this

@ingest.command("filesystem")
def ingest_filesystem(
    path: Path = typer.Argument(..., exists=True, file_okay=False),
    recursive: bool = True,
):
    """
    Ingest a local filesystem directory.
    Extraction + chunking happens locally.
    Embedding + storage happens in the backend.
    """

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

        # 3️⃣ flush batch
        if len(documents_batch) >= BATCH_SIZE:
            _send_batch(run_id, documents_batch)
            documents_batch.clear()
            sent_any = True

    # 4️⃣ flush remainder
    if documents_batch:
        _send_batch(run_id, documents_batch)
        sent_any = True

    if not sent_any:
        typer.echo("No documents found.")
        raise typer.Exit(code=0)

    typer.echo("Filesystem ingestion completed successfully.")

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


@ingest.command("thunderbird")
def ingest_thunderbird(
    mbox: str = typer.Option(..., "--mbox"),
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

    source = ThunderbirdIngestionSource(scope=scope, should_stop=lambda: False)

    documents_payload: List[Dict[str, Any]] = []

    for doc in source.iter_documents():
        documents_payload.append(
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

    if not documents_payload:
        typer.echo("No emails found.")
        raise typer.Exit(code=0)

    r = httpx.post(
        f"{API_URL}/ingest/documents",
        json={"documents": documents_payload},
        timeout=60.0,
    )
    r.raise_for_status()

    typer.echo("Thunderbird ingestion completed successfully.")

@run.command()
def list():
    r = httpx.get(f"{API_URL}/runs/list")
    r.raise_for_status()

    for run in r.json()["runs"]:
        typer.echo(run)

@run.command()
def stop_latest(source_type: str):
    r = httpx.post(f"{API_URL}/runs/stop_latest/{source_type}")
    r.raise_for_status()

    typer.echo(r.json())

@run.command()
def resume_latest(source_type: str):
    r = httpx.post(f"{API_URL}/ingest/resume_latest/{source_type}")
    r.raise_for_status()

    typer.echo(r.json())

@app.command()
def search(query: str, top_k: int = 10):
    r = httpx.post(
        f"{API_URL}/search",
        json={"query": query, "top_k": top_k},
    )
    r.raise_for_status()

    for hit in r.json()["results"]:
        typer.echo(hit)


if __name__ == "__main__":
    app()
