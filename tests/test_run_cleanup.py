from api.app.main import app
from src.sources.thunderbird.thunderbird_model import ThunderbirdIndexingScope
from src.sources.thunderbird.thunderbird_source import ThunderbirdIngestionSource
from src.sources.filesystem.filesystem_model import FilesystemIndexingScope
from src.sources.filesystem.filesystem_source import FilesystemIngestionSource
from datetime import datetime, timezone
import pytest
from pathlib import Path
import logging
import os
import json

logger = logging.getLogger(__name__)

# make sure qdrant_url is "http://qdrant_test:6333" for testing
assert os.environ.get("QDRANT_URL") == "http://qdrant_test:6333", "QDRANT_URL environment variable must be set to 'http://qdrant_test:6333' for testing"



def test_run_cleanup(client, setup_db, tmp_path, write_files_to_disk):
    test_dir, all_documents, all_ignored_docuemnts = write_files_to_disk
    test_db_path = setup_db
    pytest.MonkeyPatch().setattr("storage.metadata_db.db.DB_PATH", test_db_path)
    scope = FilesystemIndexingScope(type="filesystem", directories=[test_dir])

    run_response = client.post(
        "/runs/create",
        json={
            "source_type": "filesystem",
            "scope_json": scope.serialize(),
        }
    )

    assert run_response.status_code == 200
    run_id = str(run_response.json().get("run_id"))
    assert run_id

    mark_running_response = client.post(
        f"/runs/mark_running/{run_id}"
    )

    source = FilesystemIngestionSource(scope, should_stop=lambda: False, update_if_changed_after = (datetime.fromisoformat(run_response.json().get("started_at"))).astimezone(timezone.utc))

    documents: list[dir] = []
    
    for doc in source.iter_documents():
        for part in doc.parts:
            r = client.post(
                    "/ingest/document_part",
                    json={
                        "run_id": run_id,
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
                        "text": part.text,
                        "scope_json": scope.serialize()
                    }
            )

            assert r.status_code == 200, f"Ingesting document part with id {part.document_part_id} failed with status code {r.status_code} and response content: {r.content}"
            assert r.json().get("accepted") == True, f"Ingesting document part with id {part.document_part_id} was not accepted. Response content: {r.content}"

    
    r = client.get(
        "/chunks/number_of_chunks"
    )
    number_of_chunks_before_cleanup = r.json().get("number_of_chunks")
    r = client.get(
        "/documents/get_all_document_parts"
    )
    document_parts_before_cleanup = r.json()

    from api.app.routes.runs import cleanup_run

    scope = FilesystemIndexingScope(type="filesystem", directories=[test_dir])
    
    run_response = client.post(
        "/runs/create",
        json={
            "source_type": "filesystem",
            "scope_json": scope.serialize(),
        }
    )
    assert run_response.status_code == 200
    run_id = str(run_response.json().get("run_id"))

    # re-ingest all documents, but skip the first one to simulate a file deletion
    

    skip = True
    for doc in source.iter_documents():
        if skip:
            skip = False
            continue
        for part in doc.parts:
            r = client.post(
                    "/ingest/document_part",
                    json={
                        "run_id": str(run_id),
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
                        "text": part.text,
                        "scope_json": scope.serialize()
                    }
            )

    cleanup_run(run_id)

    r = client.get(
        "/chunks/number_of_chunks"
    )
    number_of_chunks_after_cleanup = r.json().get("number_of_chunks")
    r = client.get(
        "/documents/get_all_document_parts"
    )
    document_parts_after_cleanup = r.json()

    assert number_of_chunks_after_cleanup < number_of_chunks_before_cleanup, "Number of chunks should be reduced after cleanup"
    assert len(document_parts_after_cleanup) < len(document_parts_before_cleanup), "Number of document parts should be reduced after cleanup"



