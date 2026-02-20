import os
import asyncio
import typer
import httpx
import logging
from pathlib import Path
from typing import List, Dict, Any

from storage.metadata_db.indexing_runs import create_run
from src.core.wiring import build_chunker

from clients.cli.config import API_URL, BATCH_SIZE
from clients.cli.ingest import ingest_app 
from clients.cli.sources import sources_app 
from clients.cli.runs import run_app
from clients.cli.queue import queue_app

app = typer.Typer(no_args_is_help=True)

app.add_typer(ingest_app, name="ingest")
app.add_typer(sources_app, name="sources")
app.add_typer(run_app, name="run")
app.add_typer(queue_app, name="queue")

logger = logging.getLogger(__name__)

# Mute httpcore and httpx loggers to WARNING level
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# add a file handler to log to a file
file_handler = logging.FileHandler("ingest.log")
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

logging.basicConfig(level=logging.DEBUG, handlers=[file_handler])


# Mute everythin except the clients.cli.ingest logger to WARNING level
#logging.getLogger("clients.cli.ingest").setLevel(logging.DEBUG)

#for logger_name in logging.root.manager.loggerDict:
#    if logger_name != "clients.cli.ingest":
#        logging.getLogger(logger_name).setLevel(logging.WARNING)
#file_handler.setFormatter(formatter)
#logger.addHandler(file_handler)


@app.command()
def search(
    query: str,
    top_k: int = 10,
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Interactively open a search result"
    ),
):
    r = httpx.post(
        f"{API_URL}/search",
        json={"query": query, "top_k": top_k},
        timeout=30.0,
    )
    r.raise_for_status()

    results = r.json()["results"]

    if not results:
        typer.echo("No results.")
        return

    payloads = [hit["document_part_id"] for hit in results]

    doc_parts = httpx.post(
        f"{API_URL}/documents/batch_get",
        json={"document_part_ids": payloads},
    )
    doc_parts.raise_for_status()

    documents = {part["document_part_id"]: part for part in doc_parts.json().get("documents_parts", [])}

    typer.echo("-" * 80)
    indexed = []
    for idx, hit in enumerate(results, start=1):
        doc = documents.get(hit["document_part_id"])
        if not doc:
            continue

        source_path = doc.get("source_path", "unknown")
        typer.echo(f"[{idx}] {source_path} | score={hit['score']:.4f}")
        indexed.append(doc)
    typer.echo("-" * 80)

    if not interactive:
        return

    from clients.cli.opening import open_descriptor

    while True:
        choice = typer.prompt(
            "Open result number (empty to quit)", default="", show_default=False
        )
        if not choice:
            break

        try:
            i = int(choice) - 1
            doc = indexed[i]

            descriptor_res = httpx.get(
                f"{API_URL}/documents/open/{doc['document_part_id']}"
                )
            
            descriptor_res.raise_for_status()
            logger.debug(f"Open descriptor response: {descriptor_res.json()}")

        except (ValueError, IndexError):
            typer.echo("Invalid selection")
            continue
        
        open_descriptor(descriptor_res.json())


if __name__ == "__main__":
    app()
