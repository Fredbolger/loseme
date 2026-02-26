
import json
from typing import List
from src.sources.base.models import DocumentPart, IndexingScope
from src.sources.filesystem import FilesystemIngestionSource, FilesystemIndexingScope
from src.sources.thunderbird import ThunderbirdIngestionSource, ThunderbirdIndexingScope
import logging
logger = logging.getLogger(__name__)

from clients.cli.config import API_URL, BATCH_SIZE


def is_stop_requested(run_id: str) -> bool:
    response = httpx.get(f"{API_URL}/runs/is_stop_requested/{run_id}")
    response.raise_for_status()
    return response.json().get("stop_requested", False)

def queue_document_part(run_id: str, part: DocumentPart, scope: IndexingScope):
    response = httpx.post(
        f"{API_URL}/queue/add",
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
        timeout=1.0,
    )
    response.raise_for_status()
    logger.info(f"Queued document part with unit_locator {part.unit_locator} and content_type {part.content_type} for file {part.source_path} (Document Part ID: {part.document_part_id})")


