from fastapi import FastAPI
import logging
import sys

from api.app.routes import ingest_router, health_router, search_router, document_router

app = FastAPI(title="Local Semantic Memory API")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("api")  # Any name

app.include_router(ingest_router)
app.include_router(health_router)
app.include_router(search_router)
app.include_router(document_router)
    
logger.info("API initialized with routers.")

@app.get("/")
def root():
    return {"status": "ok"}
