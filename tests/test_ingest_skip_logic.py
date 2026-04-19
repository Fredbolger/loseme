"""
test_ingest_skip_logic.py — Ingest skip / reprocess logic.

Documents unchanged since last ingest must be skipped.
Any change to checksum, extractor, or chunker must trigger reprocessing.

Uses the API's ingest endpoint with InMemoryVectorStore + DummyEmbeddingProvider.
"""
import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from loseme_core.ids import make_logical_document_part_id, make_source_instance_id


# ---------------------------------------------------------------------------
# Module-level fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def app_client(tmp_path_factory):
    tmp_db = tmp_path_factory.mktemp("skip_db") / "skip.db"
    from pipeline.embeddings.dummy import DummyEmbeddingProvider
    from storage.vector_db.in_memory import InMemoryVectorStore

    store = InMemoryVectorStore(dimension=384)
    embedder = DummyEmbeddingProvider(dimension=384)

    with patch("storage.vector_db.runtime.get_vector_store", return_value=store), \
         patch("storage.vector_db.runtime.get_embedding_provider", return_value=embedder), \
         patch("wiring.build_embedding_provider", return_value=embedder), \
         patch("storage.metadata_db.db.DB_PATH", tmp_db):

        from storage.metadata_db.db import init_db
        init_db()
        from api.app.main import app
        from fastapi.testclient import TestClient
        yield TestClient(app)


@pytest.fixture
def run_id(app_client):
    resp = app_client.post(
        "/runs/create",
        json={
            "source_type": "filesystem",
            "scope_json": json.dumps({"type": "filesystem", "directories": ["/tmp/skip"]}),
        },
    )
    return resp.json()["run_id"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_COUNTER = 0


def _new_locator(prefix: str = "loc") -> str:
    global _COUNTER
    _COUNTER += 1
    return f"filesystem:/tmp/skip/{prefix}_{_COUNTER}.txt"


def _payload(run_id: str, text: str, unit_locator: str,
             extractor_name: str = "plaintext", extractor_version: str = "0.1",
             chunker_name: str = "simple", chunker_version: str = "1.0") -> dict:
    sid = make_source_instance_id("filesystem", "dev-skip", Path("/tmp/skip"))
    doc_id = make_logical_document_part_id(sid, unit_locator)
    checksum = hashlib.sha256(text.encode()).hexdigest()
    return {
        "run_id": run_id,
        "document_part_id": doc_id,
        "checksum": checksum,
        "source_type": "filesystem",
        "source_instance_id": sid,
        "device_id": "dev-skip",
        "source_path": "/tmp/skip/doc.txt",
        "unit_locator": unit_locator,
        "content_type": "text/plain",
        "extractor_name": extractor_name,
        "extractor_version": extractor_version,
        "metadata_json": {},
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
        "text": text,
        "scope_json": {"type": "filesystem", "directories": ["/tmp/skip"]},
    }


def _new_run(client) -> str:
    resp = client.post(
        "/runs/create",
        json={
            "source_type": "filesystem",
            "scope_json": json.dumps({"type": "filesystem", "directories": ["/tmp/skip"]}),
        },
    )
    return resp.json()["run_id"]


# ===========================================================================
# Skip unchanged document
# ===========================================================================

class TestSkipUnchangedDocument:

    def test_first_ingest_is_accepted(self, app_client):
        r1 = _new_run(app_client)
        p = _payload(r1, "hello world", _new_locator("skip"))
        resp = app_client.post("/ingest/document_part", json=p)
        assert resp.status_code == 200
        assert resp.json().get("accepted") is True

    def test_second_ingest_same_document_is_skipped(self, app_client):
        loc = _new_locator("skip2")
        r1 = _new_run(app_client)
        p1 = _payload(r1, "same content", loc)
        app_client.post("/ingest/document_part", json=p1)

        r2 = _new_run(app_client)
        p2 = _payload(r2, "same content", loc)
        resp = app_client.post("/ingest/document_part", json=p2)
        assert resp.json().get("skipped") is True

    def test_skipped_document_returns_accepted_true(self, app_client):
        loc = _new_locator("skip3")
        r1 = _new_run(app_client)
        app_client.post("/ingest/document_part", json=_payload(r1, "stable text", loc))
        r2 = _new_run(app_client)
        resp = app_client.post("/ingest/document_part", json=_payload(r2, "stable text", loc))
        assert resp.json().get("accepted") is True


# ===========================================================================
# Reprocess on change
# ===========================================================================

class TestReprocessOnChange:

    def test_changed_checksum_triggers_reprocess(self, app_client):
        loc = _new_locator("reprocess")
        r1 = _new_run(app_client)
        app_client.post("/ingest/document_part", json=_payload(r1, "original text", loc))
        r2 = _new_run(app_client)
        resp = app_client.post("/ingest/document_part", json=_payload(r2, "modified text", loc))
        assert resp.json().get("skipped") is not True

    def test_changed_extractor_version_triggers_reprocess(self, app_client):
        loc = _new_locator("extv")
        r1 = _new_run(app_client)
        app_client.post("/ingest/document_part", json=_payload(r1, "text", loc, extractor_version="0.1"))
        r2 = _new_run(app_client)
        resp = app_client.post(
            "/ingest/document_part",
            json=_payload(r2, "text", loc, extractor_version="0.2"),
        )
        assert resp.json().get("skipped") is not True

    def test_changed_extractor_name_triggers_reprocess(self, app_client):
        loc = _new_locator("extn")
        r1 = _new_run(app_client)
        app_client.post("/ingest/document_part", json=_payload(r1, "text", loc, extractor_name="plaintext"))
        r2 = _new_run(app_client)
        resp = app_client.post(
            "/ingest/document_part",
            json=_payload(r2, "text", loc, extractor_name="html"),
        )
        assert resp.json().get("skipped") is not True

    def test_force_reprocess_ignores_skip(self, app_client):
        loc = _new_locator("force")
        r1 = _new_run(app_client)
        app_client.post("/ingest/document_part", json=_payload(r1, "text", loc))
        r2 = _new_run(app_client)
        resp = app_client.post(
            "/ingest/document_part?force_reprocess=true",
            json=_payload(r2, "text", loc),
        )
        assert resp.json().get("skipped") is not True
        assert resp.json().get("accepted") is True


# ===========================================================================
# Ingest increments counters
# ===========================================================================

class TestIngestCounters:

    def test_ingest_increments_indexed_count(self, app_client):
        r = _new_run(app_client)
        # get initial count
        runs_before = {x["run_id"]: x for x in app_client.get("/runs/list").json()["runs"]}
        before = runs_before.get(r, {}).get("indexed_document_count", 0)

        loc = _new_locator("cnt")
        app_client.post("/ingest/document_part", json=_payload(r, "count me", loc))

        runs_after = {x["run_id"]: x for x in app_client.get("/runs/list").json()["runs"]}
        after = runs_after.get(r, {}).get("indexed_document_count", 0)
        assert after > before
