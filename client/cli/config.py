import os
import httpx
 
API_URL = os.environ.get("LOSEME_API_URL", "http://localhost:8000").rstrip("/")
BATCH_SIZE = 20

 
_API_KEY: str = os.environ.get("LOSEME_API_KEY", "").strip()
 
def _build_headers() -> dict:
    if _API_KEY:
        return {"X-API-Key": _API_KEY}
    return {}
 
 
def get_client(timeout: float = 30.0) -> httpx.Client:
    """
    Return a synchronous httpx.Client pre-configured with the server URL
    and (if set) the X-API-Key auth header.
 
    Usage:
        with get_client() as client:
            r = client.get("/health")
    """
    return httpx.Client(
        base_url=API_URL,
        headers=_build_headers(),
        timeout=timeout,
    )

