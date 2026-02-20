import httpx 
import typer
from clients.cli.config import API_URL
import logging
logger = logging.getLogger(__name__)

run_app = typer.Typer(no_args_is_help=True, help="Manage indexing runs.")

@run_app.command()
def list():
    r = httpx.get(f"{API_URL}/runs/list")
    r.raise_for_status()

    if not r.json().get("runs"):
        typer.echo("No runs found.")
        raise typer.Exit(code=0)

    elif len(r.json()["runs"]) == 0:
        typer.echo("No runs found.")
        raise typer.Exit(code=0)
    else:
        for run in r.json()["runs"]:
            typer.echo(run)
@run_app.command()
def stop(run_id: str):
    r = httpx.post(f"{API_URL}/runs/request_stop/{run_id}")
    r.raise_for_status()

    typer.echo(r.json())

@run_app.command()
def start(run_id: str):
    r = httpx.post(f"{API_URL}/runs/start_indexing/{run_id}")
    r.raise_for_status()
    
    typer.echo(r.json())

@run_app.command()
def stop_latest(source_type: str):
    r = httpx.post(f"{API_URL}/runs/stop_latest/{source_type}")
    r.raise_for_status()

    typer.echo(r.json())

@run_app.command()
def resume_latest(source_type: str):
    r = httpx.get(f"{API_URL}/runs/resume_latest/{source_type}")
    
    r.raise_for_status()
    
    if r.json().get("run_id") is None:
        typer.echo("No interrupted indexing run found.")
        raise typer.Exit(code=0)

    run_id = r.json().get("run_id")
    run_status = r.json().get("status")
    
    logger.debug(f"Loaded interrupted run ID: {run_id} with status: {run_status}")
    logger.debug(f"Run details: {r.json()}")
   
    typer.echo(f"Resuming interrupted run ID: {run_id} with status: {run_status}")
    
    scope = ThunderbirdIndexingScope(
        type="thunderbird",
        mbox_path=r.json().get("mbox_path"),
        ignore_patterns=r.json().get("ignore_patterns", []),
    )
    source = ThunderbirdIngestionSource(scope, should_stop=lambda: False)
    documents_batch: list[dict] = []
    sent_any = False
    for doc in source.iter_documents():
        if is_stop_requested(run_id):
            logger.info("Stop requested, terminating Thunderbird ingestion.")
            break
        response = httpx.post(
            f"{API_URL}/runs/increment_discovered/{run_id}"
        )
        add_discovered_document_to_db(
            run_id=run_id,
            source_instance_id=doc.source_id,
            content_checksum=doc.checksum,
        )
        logger.info(
            f"Processing email {doc.source_path} (ID: {doc.id}) "
            f"with {len(doc.texts)} text units and content types {doc.content_types} "
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
                "texts": doc.texts,
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
        raise typer.Exit(code=0)
    typer.echo("Resumed Thunderbird ingestion completed successfully.")



