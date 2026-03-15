import os
import httpx
from fastapi import FastAPI, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
import preview
from preview import preview_registry

import logging
import sys

logging.basicConfig(
    level=logging.DEBUG,
    stream=sys.stdout,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("client")

API_URL = os.environ.get("LOSEME_API_URL", "http://localhost:8000")

app = FastAPI(title="LoseMe Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/config")
def get_config():
    return {
        "api_url": os.environ.get("LOSEME_PUBLIC_API_URL", "http://localhost:8000"),
        "client_url": os.environ.get("LOSEME_PUBLIC_CLIENT_URL", "http://localhost:3000")
    }

@app.get("/documents/preview/{document_part_id}")
def preview_document(document_part_id: str):
    # fetch doc part from server
    r = httpx.get(f"{API_URL}/documents/by_id/{document_part_id}")
    if r.status_code == 404:
        raise HTTPException(404, "Document not found")
    r.raise_for_status()
    doc_part = r.json()

    # fetch source type from server
    r2 = httpx.get(f"{API_URL}/documents/scope/{document_part_id}")
    if r2.status_code == 404:
        raise HTTPException(404, "Scope not found")
    r2.raise_for_status()
    source_type = r2.json()["source_type"]

    generator = preview_registry.get_generator(source_type, doc_part)
    if generator is None:
        raise HTTPException(400, f"Preview not supported for source_type='{source_type}'")
    return generator.generate(doc_part).to_dict()


app.mount("/static", StaticFiles(directory="web/static"), name="static")

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    return FileResponse("web/static/views/index.html")

@app.post("/sources/scan/{source_id}")
def scan_source(source_id: str, background_tasks: BackgroundTasks):
    # fetch source details from server
    r = httpx.get(f"{API_URL}/sources/get/{source_id}")
    if r.status_code == 404:
        raise HTTPException(404, "Source not found")
    r.raise_for_status()
    source = r.json()["source"]

    source_type = source["source_type"]

    if source_type == "filesystem":
        from cli.ingest import queue_filesystem_logic
        scope = source["scope"]
        directories = scope.get("directories", [])
        if not directories:
            raise HTTPException(400, "No directories in scope")
        background_tasks.add_task(
            queue_filesystem_logic,
            path=directories[0],
            include_patterns=scope.get("include_patterns", []),
            exclude_patterns=scope.get("exclude_patterns", []),
            recursive=scope.get("recursive", True),
        )
    elif source_type == "thunderbird":
        from cli.ingest import queue_thunderbird_logic
        scope = source["scope"]
        background_tasks.add_task(
            queue_thunderbird_logic,
            mbox=scope.get("mbox_path"),
        )
    else:
        raise HTTPException(400, f"Unsupported source type: {source_type}")

    return {"status": "scanning"}
