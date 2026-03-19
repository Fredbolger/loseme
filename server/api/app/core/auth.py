"""
Optional API-key authentication middleware.

If LOSEME_API_KEY is set in the environment, every request must carry:
    X-API-Key: <value>

If the env var is empty or unset, auth is disabled (useful on a trusted LAN
or during local development).
"""
import os
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

_API_KEY = os.environ.get("LOSEME_API_KEY", "").strip()

# Paths that are always allowed without a key (health check, docs)
_EXEMPT = {"/health", "/docs", "/openapi.json", "/redoc", "/"}


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not _API_KEY:
            # Auth disabled
            return await call_next(request)

        if request.url.path in _EXEMPT:
            return await call_next(request)

        key = request.headers.get("X-API-Key", "")
        if key != _API_KEY:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing X-API-Key header"},
            )

        return await call_next(request)
