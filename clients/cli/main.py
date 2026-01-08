import typer
import httpx
import os

app = typer.Typer()
API_URL = os.environ.get("API_URL", "http://localhost:8000")


@app.command()
def ingest(path: str):
    """Ingest a folder into semantic memory."""
    r = httpx.post(
        f"{API_URL}/ingest/filesystem",
        json={"path": path},
    )
    r.raise_for_status()
    data = r.json()
    typer.echo(f"Ingested {data['documents_ingested']} documents")


@app.command()
def search(query: str, top_k: int = 5):
    """Semantic search."""
    r = httpx.post(
        f"{API_URL}/search",
        json={"query": query, "top_k": top_k},
    )
    r.raise_for_status()

    for hit in r.json()["results"]:
        typer.echo(f"{hit['score']:.3f} → {hit['metadata']}")

