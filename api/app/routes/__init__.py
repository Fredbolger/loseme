from .ingest import router as ingest_router
from .health import router as health_router
from .search import router as search_router

__all__ = ["ingest_router", "health_router"]
