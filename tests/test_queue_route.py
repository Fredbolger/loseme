from api.app.main import app
from src.sources.thunderbird.thunderbird_model import ThunderbirdIndexingScope
from src.sources.thunderbird.thunderbird_source import ThunderbirdIngestionSource
from src.sources.filesystem.filesystem_model import FilesystemIndexingScope
from src.sources.filesystem.filesystem_source import FilesystemIngestionSource
from storage.metadata_db.document_parts_queue import add_document_part_to_queue, get_next_document_part_from_queue
from datetime import datetime, timezone
import pytest
from pathlib import Path
import logging
import os
import json

logger = logging.getLogger(__name__)

# make sure qdrant_url is "http://qdrant_test:6333" for testing
assert os.environ.get("QDRANT_URL") == "http://qdrant_test:6333", "QDRANT_URL environment variable must be set to 'http://qdrant_test:6333' for testing"

def test_add_and_retreieve_part_to_queue(client, fake_mbox_path, setup_db, tmp_path):
    # Get all available routes
    route_paths = [route.path for route in client.app.router.routes]
    logger.info(f"All routes: {route_paths}")
    assert "/queue/add" in route_paths

    mbox_path = fake_mbox_path
    test_db_path = setup_db
    pytest.MonkeyPatch().setattr("storage.metadata_db.db.DB_PATH", test_db_path)
    scope = ThunderbirdIndexingScope(
            type="thunderbird",
            mbox_path=mbox_path,
            ignore_patterns=[{"field": "from", "value": "*google.com*"}],
        )

    run_response = client.post(
        "/runs/create",
        json={
            "source_type": "thunderbird",
            "scope_json": scope.serialize(),
        }
    )
    assert run_response.status_code == 200
    run_id = str(run_response.json().get("run_id"))
    assert run_id

    mark_running_response = client.post(
        f"/runs/mark_running/{run_id}"
    )

    source = ThunderbirdIngestionSource(scope, should_stop=lambda: False, update_if_changed_after = (datetime.fromisoformat(run_response.json().get("started_at"))).astimezone(timezone.utc))

    document_parts: list[dir] = []

    for doc in source.iter_documents():
        # Ingest the all document parts
        for part in doc.parts:
            r = client.post(
                    "/queue/add",
                    json={
                        "part": {
                            "document_part_id": part.document_part_id,
                            "source_type": part.source_type,
                            "checksum": part.checksum,
                            "device_id": part.device_id,
                            "source_path": part.source_path,
                            "source_instance_id": part.source_instance_id,
                            "unit_locator": part.unit_locator,
                            "content_type": part.content_type,
                            "extractor_name": part.extractor_name,
                            "extractor_version": part.extractor_version,
                            "metadata_json": part.metadata_json,
                            "created_at": part.created_at.isoformat(),
                            "updated_at": part.updated_at.isoformat(),
                            "text": part.text
                        },
                        "run_id": run_id
                    }
            )
            assert r.status_code == 200, f"Failed to add document part to queue: {r.text}" 

    # Now get the document parts back from the queue and compare
    for _ in range(len(document_parts)):
        r = client.get(f"/queue/next/{run_id}")
        assert r.status_code == 200
        part = r.json()
        assert part["run_id"] == run_id
        assert "document_part_id" in part
        assert "source_type" in part
        assert "checksum" in part
        assert "device_id" in part
        assert "source_path" in part
        assert "source_instance_id" in part
        assert "unit_locator" in part
        assert "content_type" in part
        assert "extractor_name" in part
        assert "extractor_version" in part
        assert "metadata_json" in part
        assert "created_at" in part
        assert "updated_at" in part

