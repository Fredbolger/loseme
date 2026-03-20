import os
from pathlib import Path
import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from cli.config import API_URL, _build_headers, get_client

app = FastAPI(title="LoseMe Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Config endpoint (consumed by app.js on boot) ─────────────
@app.get("/config")
def get_config():
    return {
        "api_url": os.environ.get("LOSEME_API_URL", "http://localhost:8000"),
        "api_key": os.environ.get("LOSEME_API_KEY", ""),
        "client_url": os.environ.get("LOSEME_CLIENT_URL", "http://localhost:3000"),
        "preview_base": "",  # empty = same origin (this web client)
    }


# ── Client-side preview (reads local files, talks to server for metadata) ──
@app.get("/documents/preview/{document_part_id}")
def preview_document(document_part_id: str):
    with httpx.Client(base_url=API_URL, headers=_build_headers(), timeout=10.0) as client:
        r = client.get(f"/documents/{document_part_id}")
        if r.status_code == 404:
            raise HTTPException(404, "Document not found")
        r.raise_for_status()
        doc_part = r.json().get("document_part") or r.json()

    from api.preview import preview_registry
    source_type = doc_part.get("source_type", "filesystem")
    generator = preview_registry.get_generator(source_type, doc_part)
    if generator is None:
        raise HTTPException(400, f"Preview not supported for source_type='{source_type}'")
    return generator.generate(doc_part).to_dict()


# ── Client-side scan (triggers local ingestion, not server-side) ────────────
@app.post("/sources/scan/{source_id}")
def scan_source(source_id: str, background_tasks: BackgroundTasks):
    with get_client() as client:
        r = client.get(f"/sources/get_all_sources")
        r.raise_for_status()

    sources = r.json().get("sources", [])
    source = next((s for s in sources if s["id"] == source_id), None)
    if source is None:
        raise HTTPException(404, "Source not found")

    source_type = source["source_type"]
    scope = source["scope"]

    # Compare the source.devide_id with the current device ID to prevent scanning a source that belongs to another device

    if source["device_id"] != os.environ.get("LOSEME_DEVICE_ID"):
        raise HTTPException(403, "Cannot scan source that belongs to another device")

    if source_type == "filesystem":
        from cli.ingest import queue_filesystem_logic
        for directory in scope.get("directories", []):
            background_tasks.add_task(
                queue_filesystem_logic,
                path=directory,
                recursive=scope.get("recursive", True),
                include_patterns=scope.get("include_patterns", []),
                exclude_patterns=scope.get("exclude_patterns", []),
            )

    elif source_type == "thunderbird":
        from cli.ingest import queue_thunderbird_logic
        background_tasks.add_task(
            queue_thunderbird_logic,
            mbox=scope.get("mbox_path"),
            ignore_from=[
                p["value"]
                for p in scope.get("ignore_patterns", [])
                if p.get("field") == "from"
            ],
        )

    else:
        raise HTTPException(400, f"Unsupported source type: {source_type}")

    return {"status": "scanning"}


BASE_DIR = Path(__file__).parent

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    return FileResponse(BASE_DIR / "static/views/index.html")
