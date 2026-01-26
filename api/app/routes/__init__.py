from .ingest import router as ingest_router
from .health import router as health_router
from .search import router as search_router
from .documents import router as document_router
from .chunks import router as chunk_router

__all__ = ["ingest_router", "health_router", "search_router", "documents_router", "chunk_router"]
