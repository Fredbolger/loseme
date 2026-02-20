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

def test_ingest_and_seach_route_thunderbird(client, fake_mbox_path, setup_db, tmp_path):
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

            document_parts.append(part.model_dump(mode="json"))
            assert document_parts[-1].get("source_type") == "thunderbird"
            source_path = document_parts[-1].get("source_path")
            # make sure the source path is correct and starts with the mbox path
            assert source_path.startswith(mbox_path), f"Source path {source_path} does not start with mbox path {mbox_path}"


    r = client.get(
            "/chunks/number_of_chunks"
            )
    assert r.status_code == 200
    assert r.json().get("number_of_chunks") > 0

    query_text = "What is the content of the email with subject 'Meeting Notes'?"
    search_response = client.post(
        "/search",
        json={
            "query": query_text,
            "top_k": 3
        }
    )
    assert search_response.status_code == 200
    results = search_response.json().get("results")
    assert isinstance(results, list)

def test_ingest_route_with_invalid_run_id(client, setup_db):
    test_db_path = setup_db
    pytest.MonkeyPatch().setattr("storage.metadata_db.db.DB_PATH", test_db_path)
    invalid_run_id = "non-existent-run-id"
    documents = [{"id": "doc-1","source_type": "thunderbird", "source_id": "doc-1", "device_id": "test-device", "source_path" : "/home/user/.thunderbird/Inbox/doc-1", "checksum": "checksum-1", "mbox_path": "/home/user/.thunderbird/Inbox", "parts": [{"unit_locator": "message_part://0", "content_type": "text/plain", "extractor_name": "plaintext", "extractor_version": "0.1", "text": "Hello world"}]}]
    
    document_part = {"run_id": invalid_run_id,
                     "document_part_id": "part-1",
                     "source_type": "thunderbird",
                     "checksum": "checksum-1",
                     "device_id": "test-device",
                     "source_path": "/home/user/.thunderbird/Inbox/doc-1",
                     "source_instance_id": "thunderbird:test-device:/home/user/.thunderbird/Inbox",
                     "unit_locator": "message_part://0",
                     "content_type": "text/plain",
                     "extractor_name": "plaintext",
                     "extractor_version": "0.1",
                     "metadata_json": {},
                     "created_at": datetime.utcnow().isoformat(),
                     "updated_at": datetime.utcnow().isoformat(),
                     "text": "Hello world",
                     "scope_json": ThunderbirdIndexingScope(
                        type="thunderbird",
                        mbox_path="/home/user/.thunderbird/Inbox",
                        ignore_patterns=[{"field": "from", "value": "*google.com*"}],
                    ).serialize()
                    }

    r = client.post(
        f"/ingest/document_part",
        json=document_part
    )

    assert r.status_code == 404
    assert r.json().get("detail") == f"Run with ID {invalid_run_id} not found"


def test_ingest_and_search_route_filesystem(client, setup_db, tmp_path, write_files_to_disk):
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
    assert r.status_code == 200
    assert r.json().get("number_of_chunks") > 0

    query_text = "What is the content of the file named 'file1.txt'?"
    search_response = client.post(
        "/search",
        json={
            "query": query_text,
            "top_k": 3
        }
    )
    assert search_response.status_code == 200
    results = search_response.json().get("results")
    assert isinstance(results, list)

def test_filesystem_ingestion_does_not_reprocess_unchanged_files(client, setup_db, tmp_path, write_files_to_disk):
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

    
    assert r.status_code == 200
    initial_chunk_count = r.json().get("number_of_chunks")
    assert initial_chunk_count > 0

    r = client.get(
            "/documents/get_all_document_parts"
            )
    assert r.status_code == 200
    initial_document_parts = r.json()

    # Run the ingestion again without changing files
    source = FilesystemIngestionSource(scope, should_stop=lambda: False, update_if_changed_after = (datetime.fromisoformat(run_response.json().get("started_at"))).astimezone(timezone.utc))
    documents = []
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
    assert r.status_code == 200
    new_chunk_count = r.json().get("number_of_chunks")
    assert new_chunk_count == initial_chunk_count, "Unchanged files should not be reprocessed and chunk count should remain the same"
    
    r = client.get(
            "/documents/get_all_document_parts"
            )
    assert r.status_code == 200
    new_document_parts = r.json()

    for old_doc_part, new_doc_part in zip(initial_document_parts, new_document_parts):
        old_doc_part = old_doc_part.get("part")
        new_doc_part = new_doc_part.get("part")
        for key in old_doc_part.keys():
            # The documents should only differ in their update and indexing times
            if key in ["updated_at", "last_indexed_at"]:
                assert old_doc_part[key] != new_doc_part[key], f"updated_at field should be different since the document part is updated with the same content but new metadata (updated_at) but they are the same: {old_doc_part[key]}"
            else:
                assert old_doc_part[key] == new_doc_part[key], f"Document parts should be the same for unchanged files but they differ in field {key}. Old document part: {old_doc_part}, new document part: {new_doc_part}"

def test_filesystem_ingestion_reprocesses_on_extractor_version_update(client, setup_db, tmp_path, write_files_to_disk):
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

    
    assert r.status_code == 200
    initial_chunk_count = r.json().get("number_of_chunks")
    assert initial_chunk_count > 0

    r = client.get(
            "/documents/get_all_document_parts"
            )
    assert r.status_code == 200
    initial_document_parts = r.json()
    

    old_python_documents_chunk_ids = []
    for part in initial_document_parts:
        part = part.get("part")
        if part.get("extractor_name") == "python":
                old_python_documents_chunk_ids.append(part.get("chunk_ids"))

    assert len(old_python_documents_chunk_ids) > 0, "There should be some documents with the python_extractor in the initial ingestion for this test to be valid"

    #####################
    ### New ingestion ###
    #####################

    ### Run the ingestion again without changing the files ###
    ### but with updated extractor version                 ###

    source = FilesystemIngestionSource(scope, should_stop=lambda: False, update_if_changed_after = (datetime.fromisoformat(run_response.json().get("started_at"))).astimezone(timezone.utc))

    documents = []
    python_files = []
    for doc_id, doc in enumerate(source.iter_documents()):
        if doc.source_path.endswith(".py"):
            python_files.append(doc_id)
    
        documents.append(doc.model_dump(mode="json"))
   
    # Change the extractor version for python files to simulate an extractor update that should trigger reprocessing
    for doc_id in python_files:
        for part_id, _ in enumerate(documents[doc_id]["parts"]):
            documents[doc_id]["parts"][part_id]["extractor_version"] = "999.0"  # set to a very high version to simulate an update

    for doc in documents:
        for part in doc["parts"]:
            r = client.post(
                    "/ingest/document_part",
                    json={
                        "run_id": run_id,
                        "document_part_id": part["document_part_id"],
                        "source_type": part["source_type"],
                        "checksum": part["checksum"],
                        "device_id": part["device_id"],
                        "source_path": part["source_path"],
                        "source_instance_id": part["source_instance_id"],
                        "unit_locator": part["unit_locator"],
                        "content_type": part["content_type"],
                        "extractor_name": part["extractor_name"],
                        "extractor_version": part["extractor_version"],
                        "metadata_json": part["metadata_json"],
                        "created_at": part["created_at"],
                        "updated_at": datetime.utcnow().isoformat(),
                        "text": part["text"],
                        "scope_json": scope.serialize()
                    }
            )

    r = client.get(
            "/chunks/number_of_chunks"
            )

    assert r.status_code == 200
    new_chunk_count = r.json().get("number_of_chunks")
    
    r = client.get(
            "/documents/get_all_document_parts"
            )
    assert r.status_code == 200
    new_document_parts = r.json()
    
    new_python_documents_chunk_ids = []

    for part in new_document_parts:
        part = part.get("part")
        if part.get("extractor_name") == "python":
             new_python_documents_chunk_ids.append(part.get("chunk_ids"))

    # All old chunk_ids for the python files should be missing

    for old_chunk_ids in old_python_documents_chunk_ids:
        for chunk_id in old_chunk_ids:
            r = client.get(
                f"/chunks/get_chunk_by_id/{chunk_id}"
            )
            logger.debug(f"Checking if old chunk with id {chunk_id} still exists after re-ingestion with updated extractor version. Response status code: {r.status_code}, response content: {r.content}")
            assert r.status_code == 404, f"Chunk with id {chunk_id} should have been deleted after re-ingestion with updated extractor version"

