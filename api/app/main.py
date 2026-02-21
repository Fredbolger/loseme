from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys

from api.app.routes import ingest_router, health_router, search_router, document_router, chunk_router, runs_router, sources_router, queue_router
from contextlib import asynccontextmanager
from storage.metadata_db.db import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    logger.info("Starting up the API...")
    init_db()
    yield
    # Shutdown actions
    logger.info("Shutting down the API...")

app = FastAPI(
        title="Local Semantic Memory API",
        lifespan=lifespan
    )
# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    stream=sys.stdout,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("api")  # Any name
# mute httpx logger
logging.getLogger("httpx").setLevel(logging.WARNING)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(ingest_router)
app.include_router(health_router)
app.include_router(search_router)
app.include_router(document_router)
app.include_router(chunk_router)
app.include_router(runs_router)
app.include_router(sources_router)
app.include_router(queue_router)
    
logger.info("API initialized with routers.")

@app.get("/")
def root():
    return {"status": "ok"}
