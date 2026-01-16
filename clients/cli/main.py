import typer
import httpx
import os
from collections import defaultdict
from clients.cli.opening import open_path
import warnings

app = typer.Typer(no_args_is_help=True)
API_URL = os.environ.get("API_URL")

if API_URL is None:
    warnings.warn("API_URL environment variable is not set. Defaulting to 'http://localhost:8000'.", UserWarning)
    API_URL = "http://localhost:8000"

@app.command()
def ingest(path: str):
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
            f"{i}) {doc['docker_path']}  score={score:.3f}  chunks={count}"
        )

    choice = typer.prompt("Open document", type=int)
    selected = documents[choice - 1][0]
    open_path(selected["source_path"])


@app.command()
def get_document(document_id: str):
    """Retrieve document metadata by document ID."""
    r = httpx.get(f"{API_URL}/documents/{document_id}")
    if r.status_code == 404:
        typer.echo("Document not found")
        raise typer.Exit(code=1)
    r.raise_for_status()
    document = r.json()
    typer.echo(document)


if __name__ == "__main__":
    app()
