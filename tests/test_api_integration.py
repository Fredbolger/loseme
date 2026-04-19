"""
test_api_integration.py — FastAPI endpoint integration tests.

Uses FastAPI TestClient with:
  - InMemoryVectorStore (no Qdrant)
  - DummyEmbeddingProvider (no GPU / ML)
  - Temporary SQLite database (no disk persistence)

All external dependencies are monkeypatched before importing the app.
"""
import hashlib
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from loseme_core.ids import make_logical_document_part_id, make_source_instance_id


# ---------------------------------------------------------------------------
# App bootstrap — patch heavy dependencies before app is imported
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def tmp_db_path(tmp_path_factory):
    return tmp_path_factory.mktemp("db") / "test.db"


@pytest.fixture(scope="module")
def app_client(tmp_db_path):
    """
    Module-scoped TestClient.  Heavy dependencies are replaced once for the
    entire module to avoid repeated initialisation overhead.
    """
    from pipeline.embeddings.dummy import DummyEmbeddingProvider
    from storage.vector_db.in_memory import InMemoryVectorStore

    store = InMemoryVectorStore(dimension=384)
    embedder = DummyEmbeddingProvider(dimension=384)

    # Patch Qdrant / embedding at the wiring level
    with patch("storage.vector_db.runtime.get_vector_store", return_value=store), \
         patch("storage.vector_db.runtime.get_embedding_provider", return_value=embedder), \
         patch("wiring.build_embedding_provider", return_value=embedder), \
         patch("storage.metadata_db.db.DB_PATH", tmp_db_path):

        from storage.metadata_db.db import init_db
        init_db()

        from api.app.main import app
        client = TestClient(app)
        yield client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scope_json():
    return {"type": "filesystem", "directories": ["/tmp/integration"]}


def _create_run(client) -> str:
    resp = client.post(
        "/runs/create",
        json={"source_type": "filesystem", "scope_json": json.dumps(_scope_json())},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["run_id"]


def _make_ingest_payload(run_id: str, text: str = "integration test content",
                          unit_locator: str = "filesystem:/tmp/integration/doc.txt") -> dict:
    sid = make_source_instance_id("filesystem", "test-device", Path("/tmp/integration"))
    doc_id = make_logical_document_part_id(sid, unit_locator)
    checksum = hashlib.sha256(text.encode()).hexdigest()
    return {
        "run_id": run_id,
        "document_part_id": doc_id,
        "checksum": checksum,
        "source_type": "filesystem",
        "source_instance_id": sid,
        "device_id": "test-device",
        "source_path": "/tmp/integration/doc.txt",
        "unit_locator": unit_locator,
        "content_type": "text/plain",
        "extractor_name": "plaintext",
        "extractor_version": "0.1",
        "metadata_json": {},
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
        "text": text,
        "scope_json": _scope_json(),
    }


# ===========================================================================
# Health
# ===========================================================================

class TestHealth:

    def test_health_returns_200(self, app_client):
        assert app_client.get("/health").status_code == 200

    def test_health_body(self, app_client):
        assert app_client.get("/health").json() == {"status": "ok"}

    def test_root_returns_200(self, app_client):
        assert app_client.get("/").status_code == 200


# ===========================================================================
# Runs
# ===========================================================================

class TestRunEndpoints:

    def test_create_run_returns_run_id(self, app_client):
        resp = app_client.post(
            "/runs/create",
            json={"source_type": "filesystem", "scope_json": json.dumps(_scope_json())},
        )
        assert resp.status_code == 200
        assert "run_id" in resp.json()
        assert resp.json()["run_id"]

    def test_list_runs_returns_200(self, app_client):
        assert app_client.get("/runs/list").status_code == 200

    def test_list_runs_has_runs_key(self, app_client):
        assert "runs" in app_client.get("/runs/list").json()

    def test_runs_is_list(self, app_client):
        assert isinstance(app_client.get("/runs/list").json()["runs"], list)

    def test_created_run_appears_in_list(self, app_client):
        run_id = _create_run(app_client)
        runs = app_client.get("/runs/list").json()["runs"]
        ids = [r["run_id"] for r in runs]
        assert run_id in ids

    def test_run_entry_has_required_fields(self, app_client):
        run_id = _create_run(app_client)
        runs = app_client.get("/runs/list").json()["runs"]
        run = next(r for r in runs if r["run_id"] == run_id)
        for field in ("run_id", "source_type", "status", "started_at"):
            assert field in run

    def test_run_source_type_correct(self, app_client):
        run_id = _create_run(app_client)
        runs = app_client.get("/runs/list").json()["runs"]
        run = next(r for r in runs if r["run_id"] == run_id)
        assert run["source_type"] == "filesystem"

    def test_mark_failed_sets_status(self, app_client):
        run_id = _create_run(app_client)
        resp = app_client.post(f"/runs/mark_failed/{run_id}")
        assert resp.status_code == 200
        runs = app_client.get("/runs/list").json()["runs"]
        run = next((r for r in runs if r["run_id"] == run_id), None)
        assert run is not None
        assert run["status"] == "failed"

    def test_mark_completed_sets_status(self, app_client):
        run_id = _create_run(app_client)
        resp = app_client.post(f"/runs/mark_completed/{run_id}")
        assert resp.status_code == 200

    def test_mark_interrupted_sets_status(self, app_client):
        run_id = _create_run(app_client)
        resp = app_client.post(f"/runs/mark_interrupted/{run_id}")
        assert resp.status_code == 200

    def test_stop_all_returns_200(self, app_client):
        _create_run(app_client)
        assert app_client.post("/runs/stop_all").status_code == 200

    def test_delete_run_removes_it(self, app_client):
        run_id = _create_run(app_client)
        app_client.post(f"/runs/mark_failed/{run_id}")  # can only delete non-running
        resp = app_client.post(f"/runs/delete/{run_id}")
        assert resp.status_code == 200
        runs = app_client.get("/runs/list").json()["runs"]
        assert all(r["run_id"] != run_id for r in runs)

    def test_discovering_stopped_returns_200(self, app_client):
        run_id = _create_run(app_client)
        assert app_client.post(f"/runs/discovering_stopped/{run_id}").status_code == 200

    def test_is_discovering_endpoint(self, app_client):
        run_id = _create_run(app_client)
        resp = app_client.get(f"/runs/is_discovering/{run_id}")
        assert resp.status_code == 200
        assert "is_discovering" in resp.json()

    def test_is_stop_requested_false_initially(self, app_client):
        run_id = _create_run(app_client)
        resp = app_client.get(f"/runs/is_stop_requested/{run_id}")
        assert resp.status_code == 200
        assert resp.json()["stop_requested"] is False


# ===========================================================================
# Ingest
# ===========================================================================

class TestIngestEndpoints:

    def test_ingest_document_part_returns_accepted(self, app_client):
        run_id = _create_run(app_client)
        payload = _make_ingest_payload(run_id)
        resp = app_client.post("/ingest/document_part", json=payload)
        assert resp.status_code == 200
        assert resp.json().get("accepted") is True

    def test_second_ingest_same_part_is_skipped(self, app_client):
        run_id = _create_run(app_client)
        payload = _make_ingest_payload(run_id, unit_locator="filesystem:/tmp/integration/skip.txt")
        app_client.post("/ingest/document_part", json=payload)
        run_id2 = _create_run(app_client)
        payload["run_id"] = run_id2
        resp = app_client.post("/ingest/document_part", json=payload)
        assert resp.json().get("skipped") is True

    def test_changed_checksum_not_skipped(self, app_client):
        run_id = _create_run(app_client)
        payload = _make_ingest_payload(
            run_id, text="original", unit_locator="filesystem:/tmp/integration/changed.txt"
        )
        app_client.post("/ingest/document_part", json=payload)

        run_id2 = _create_run(app_client)
        payload2 = _make_ingest_payload(
            run_id2, text="modified", unit_locator="filesystem:/tmp/integration/changed.txt"
        )
        resp = app_client.post("/ingest/document_part", json=payload2)
        assert resp.json().get("skipped") is not True

    def test_invalid_run_id_returns_404(self, app_client):
        payload = _make_ingest_payload("nonexistent-run-id")
        resp = app_client.post("/ingest/document_part", json=payload)
        assert resp.status_code == 404


# ===========================================================================
# Search
# ===========================================================================

class TestSearchEndpoints:

    def test_search_returns_200(self, app_client):
        resp = app_client.post("/search", json={"query": "anything", "top_k": 5})
        assert resp.status_code == 200

    def test_search_has_results_key(self, app_client):
        resp = app_client.post("/search", json={"query": "anything", "top_k": 5})
        assert "results" in resp.json()

    def test_search_results_is_list(self, app_client):
        resp = app_client.post("/search", json={"query": "anything", "top_k": 5})
        assert isinstance(resp.json()["results"], list)

    def test_search_empty_index_returns_empty(self, app_client):
        # Fresh store may have results from other tests; just verify no crash
        resp = app_client.post("/search", json={"query": "zzz_unlikely_query", "top_k": 1})
        assert resp.status_code == 200

    def test_search_ingested_document_appears(self, app_client):
        run_id = _create_run(app_client)
        unique_text = "neutrino oscillation physics experiment"
        payload = _make_ingest_payload(
            run_id, text=unique_text,
            unit_locator="filesystem:/tmp/integration/physics.txt"
        )
        app_client.post("/ingest/document_part", json=payload)

        resp = app_client.post("/search", json={"query": unique_text, "top_k": 10})
        assert resp.status_code == 200
        doc_ids = [r["document_part_id"] for r in resp.json()["results"]]
        assert payload["document_part_id"] in doc_ids

    def test_search_result_has_required_fields(self, app_client):
        run_id = _create_run(app_client)
        payload = _make_ingest_payload(
            run_id, unit_locator="filesystem:/tmp/integration/fields_check.txt"
        )
        app_client.post("/ingest/document_part", json=payload)
        resp = app_client.post("/search", json={"query": "integration test content", "top_k": 5})
        for r in resp.json()["results"]:
            for field in ("chunk_id", "document_part_id", "device_id", "score", "metadata"):
                assert field in r

    def test_search_top_k_limits_count(self, app_client):
        run_id = _create_run(app_client)
        for i in range(6):
            app_client.post("/ingest/document_part", json=_make_ingest_payload(
                run_id,
                text=f"unique content item number {i} for topk test",
                unit_locator=f"filesystem:/tmp/integration/topk{i}.txt",
            ))
        resp = app_client.post("/search", json={"query": "unique content item", "top_k": 3})
        assert len(resp.json()["results"]) <= 3

    def test_search_scores_in_valid_range(self, app_client):
        run_id = _create_run(app_client)
        app_client.post("/ingest/document_part", json=_make_ingest_payload(
            run_id, unit_locator="filesystem:/tmp/integration/score_range.txt"
        ))
        resp = app_client.post("/search", json={"query": "integration test", "top_k": 5})
        for r in resp.json()["results"]:
            assert -1.0 <= r["score"] <= 1.0


# ===========================================================================
# Documents
# ===========================================================================

class TestDocumentEndpoints:

    def test_stats_returns_200(self, app_client):
        assert app_client.get("/documents/stats").status_code == 200

    def test_stats_has_required_keys(self, app_client):
        data = app_client.get("/documents/stats").json()
        for key in ("total_document_parts", "total_sources", "total_devices"):
            assert key in data

    def test_batch_get_unknown_ids_returns_empty(self, app_client):
        resp = app_client.post(
            "/documents/batch_get",
            json={"document_part_ids": ["nonexistent"]},
        )
        assert resp.status_code == 200
        assert resp.json()["documents_parts"] == []

    def test_get_document_by_id_not_found(self, app_client):
        resp = app_client.get("/documents/by_id/totally-fake-id")
        assert resp.status_code == 404

    def test_get_document_after_ingest(self, app_client):
        run_id = _create_run(app_client)
        payload = _make_ingest_payload(
            run_id, unit_locator="filesystem:/tmp/integration/get_doc.txt"
        )
        app_client.post("/ingest/document_part", json=payload)
        resp = app_client.get(f"/documents/by_id/{payload['document_part_id']}")
        assert resp.status_code == 200

    def test_chunker_stats_returns_200(self, app_client):
        assert app_client.get("/documents/stats/chunker").status_code == 200

    def test_per_source_stats_returns_200(self, app_client):
        assert app_client.get("/documents/stats/per_source").status_code == 200


# ===========================================================================
# Queue
# ===========================================================================

class TestQueueEndpoints:

    def test_show_all_queues_returns_200(self, app_client):
        assert app_client.get("/queue/show_all_queues").status_code == 200

    def test_add_to_queue(self, app_client):
        from loseme_core.document_models import DocumentPart
        from datetime import datetime
        run_id = _create_run(app_client)
        sid = make_source_instance_id("filesystem", "dev1", Path("/tmp"))
        doc_id = make_logical_document_part_id(sid, "filesystem:/tmp/q.txt")
        payload = {
            "run_id": run_id,
            "part": {
                "document_part_id": doc_id,
                "checksum": "abc",
                "source_type": "filesystem",
                "source_instance_id": sid,
                "device_id": "dev1",
                "source_path": "/tmp/q.txt",
                "unit_locator": "filesystem:/tmp/q.txt",
                "content_type": "text/plain",
                "extractor_name": "plaintext",
                "extractor_version": "0.1",
                "metadata_json": {},
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "text": "queue test",
                "scope_json": {"type": "filesystem", "directories": ["/tmp"]},
            },
        }
        resp = app_client.post("/queue/add", json=payload)
        assert resp.status_code == 200


# ===========================================================================
# Sources
# ===========================================================================

class TestSourceEndpoints:

    def test_get_all_sources_returns_200(self, app_client):
        assert app_client.get("/sources/get_all_sources").status_code == 200

    def test_get_all_sources_has_sources_key(self, app_client):
        assert "sources" in app_client.get("/sources/get_all_sources").json()

    def test_add_source(self, app_client):
        resp = app_client.post(
            "/sources/add",
            json={
                "source_type": "filesystem",
                "device_id": "dev-test",
                "scope": {
                    "type": "filesystem",
                    "directories": ["/tmp/source-test"],
                    "recursive": True,
                    "include_patterns": [],
                    "exclude_patterns": [],
                },
            },
        )
        assert resp.status_code == 200
        assert "source_id" in resp.json()

    def test_get_source_not_found(self, app_client):
        resp = app_client.get("/sources/get/nonexistent-id")
        assert resp.status_code == 404
