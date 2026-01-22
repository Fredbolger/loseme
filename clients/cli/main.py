import typer
import httpx
import os
from collections import defaultdict
from clients.cli.opening import open_path
import warnings
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

app = typer.Typer(no_args_is_help=True)
API_URL = os.environ.get("API_URL")
LOSEME_SOURCE_ROOT_HOST = os.environ.get("LOSEME_SOURCE_ROOT_HOST")

if API_URL is None:
    warnings.warn("API_URL environment variable is not set. Defaulting to 'http://localhost:8000'.", UserWarning)
    API_URL = "http://localhost:8000"

if LOSEME_SOURCE_ROOT_HOST is None:
    warnings.warn("LOSEME_SOURCE_ROOT_HOST environment variable is not set. Defaulting to '/host_data'.", UserWarning)
    LOSEME_SOURCE_ROOT_HOST = "/run/media/ben/data/Nextcloud/Home/H_Projects/loseme/data/"

def parse_kv_args(args: list[str]) -> dict:
    data: dict[str, Any] = {}

    for arg in args:
        if "=" not in arg:
            raise typer.BadParameter(
                f"Invalid argument '{arg}'. Expected key=value."
            )

        key, raw_value = arg.split("=", 1)
        value = coerce_value(raw_value)

        if key in data:
            if not isinstance(data[key], list):
                data[key] = [data[key]]
            data[key].append(value)
        else:
            data[key] = value

    return data


def coerce_value(value: str):
    if value.lower() in ("true", "false"):
        return value.lower() == "true"

    if value.isdigit():
        return int(value)

    return value


@app.command()
def ingest_filesystem(path: str):
    """Ingest a folder into semantic memory."""
    r = httpx.post(
        f"{API_URL}/ingest/filesystem",
        json={"directories": [path],
              "recursive": True,
              "include_patterns": [],
              "exclude_patterns": []
              },
    )
    r.raise_for_status()
    data = r.json()
    typer.echo(f"Ingestion started. Run ID: {data['run_id']}")


@app.command(context_settings={"allow_extra_args": True})
def ingest(
    ctx: typer.Context,
    type: str,
):
    data = parse_kv_args(ctx.args)
    
    logger.debug(f"Ingesting with type: {type}, data: {data}")

    payload = {
        "type": type,
        "data": data,
    }

    r = httpx.post(f"{API_URL}/ingest/", json=payload)
    r.raise_for_status()

    result = r.json()
    typer.echo(f"Ingestion started. Run ID: {result['run_id']}")

@app.command()
def search(query: str, top_k: int = 10, interactive: bool = False):
    """Semantic search."""
    r = httpx.post(
        f"{API_URL}/search",
        json={"query": query, "top_k": top_k},
    )
    r.raise_for_status()
    hits = r.json()["results"]

    if not interactive:
        for hit in hits:
            typer.echo(f"Hit is: {hit}")
        return

    # group by document_id
    grouped = defaultdict(list)
    for hit in hits:
        grouped[hit["document_id"]].append(hit)

    documents = []
    for doc_id, chunks in grouped.items():
        doc = httpx.get(f"{API_URL}/documents/{doc_id}").json()
        score = max(c["score"] for c in chunks)
        documents.append((doc, score, len(chunks)))

    documents.sort(key=lambda x: x[1], reverse=True)
    
    if len(documents) == 0:
        typer.echo("No documents found.")
        raise typer.Exit(code=0)

    for i, (doc, score, count) in enumerate(documents, start=1):
        typer.echo(
            f"{i}) {doc['source_path']}  score={score:.3f}  chunks={count}"
        )

    choice = typer.prompt("Open document", type=int)
    selected = documents[choice - 1][0]
    logical_path = os.path.join(LOSEME_SOURCE_ROOT_HOST, selected["source_path"].lstrip("/"))
    open_path(logical_path)


@app.command()
def get_document(document_id: str):
    """Retrieve document metadata by document ID."""
    r = httpx.get(f"{API_URL}/documents/{document_id}")
    if r.status_code == 404:
        typer.echo(f"Document with ID {document_id} not found.")
        raise typer.Exit(code=1)
    r.raise_for_status()
    document = r.json()
    typer.echo(document)

@app.command()
def stop_latest_run(source_type: str):
    """Stop the latest ingestion run for a given source type."""
    r = httpx.post(f"{API_URL}/ingest/stop_latest/{source_type}")
    if r.status_code == 404:
        typer.echo(f"No active ingestion run found for source type '{source_type}'.")
        raise typer.Exit(code=1)
    r.raise_for_status()
    typer.echo(f"Stop request sent for latest ingestion run of type '{source_type}'.")

@app.command()
def resume_latest_run(source_type: str):
    """Resume the latest interrupted ingestion run for a given source type."""
    r = httpx.post(f"{API_URL}/ingest/resume_latest/{source_type}")
    if r.status_code == 404:
        typer.echo(f"No interrupted ingestion run found for source type '{source_type}'.")
        raise typer.Exit(code=1)
    r.raise_for_status()
    data = r.json()
    typer.echo(f"Resumed ingestion run. Run ID: {data['run_id']}")

if __name__ == "__main__":
    app()
