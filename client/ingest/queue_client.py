import httpx
import logging
import os
from loseme_core.models import DocumentPart, IndexingScope

logger = logging.getLogger(__name__)

API_URL = os.environ.get("LOSEME_API_URL", "http://localhost:8000")

def queue_document_part(run_id: str, part: DocumentPart, scope: IndexingScope, api_url: str = API_URL):
    response = httpx.post(
        f"{api_url}/queue/add",
        json={
            "part": {
                "document_part_id": part.document_part_id,
                "source_type": part.source_type,
                "checksum": part.checksum,
                "device_id": part.device_id,
                "source_path": str(part.source_path),
                "source_instance_id": part.source_instance_id,
                "unit_locator": part.unit_locator,
                "content_type": part.content_type,
                "extractor_name": part.extractor_name,
                "extractor_version": part.extractor_version,
                "metadata_json": part.metadata_json,
                "created_at": part.created_at.isoformat(),
                "updated_at": part.updated_at.isoformat(),
                "text": part.text,
                "scope_json": scope.serialize(),
            },
            "run_id": run_id,
        },
        timeout=5.0,
    )
    response.raise_for_status()
    logger.info(f"Queued document part {part.unit_locator} (run {run_id})")
