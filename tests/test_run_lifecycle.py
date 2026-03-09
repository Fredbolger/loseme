"""
Run lifecycle tests.

Resumable indexing is a core guarantee of this system. It depends entirely
on the run status machine being correct. An incorrect transition can cause:
  - Double-indexing (running → running without cleanup)
  - Silent data loss (interrupting a run that is then never resumed)
  - Zombie runs that block future indexing

Tests cover: creation, start, discovering_stopped, mark_failed, list, stop_all.
"""

import pytest

from src.sources.filesystem.filesystem_model import FilesystemIndexingScope
from storage.metadata_db.indexing_runs import create_run, load_latest_run_by_scope
from tests.helpers import client

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _create_run_via_api(path: str) -> str:
    scope = FilesystemIndexingScope(type="filesystem", directories=[path])
    resp = client.post(
        "/runs/create",
        json={"source_type": "filesystem", "scope_json": scope.serialize()},
    )
    assert resp.status_code == 200, resp.text
    run_id = resp.json()["run_id"]
    assert run_id, "run_id must not be empty"
    return run_id


def _start_run(run_id: str):
    resp = client.post(f"/runs/start_indexing/{run_id}")
    assert resp.status_code == 200, resp.text
    return resp


def _get_run_from_list(run_id: str) -> dict | None:
    runs = client.get("/runs/list").json()["runs"]
    matches = [r for r in runs if r["run_id"] == run_id]
    return matches[0] if matches else None

class TestRunCreation:

    def test_api_returns_run_id(self, setup_db, api_client):
        run_id = _create_run_via_api(api_client, "/tmp/creation-test")
        assert isinstance(run_id, str)

    def test_run_appears_in_list_after_creation(self, setup_db, api_client):
        run_id = _create_run_via_api(api_client, "/tmp/list-after-creation")
        assert _get_run_from_list(api_client, run_id) is not None

    def test_initial_status_is_valid(self, setup_db):
        scope = FilesystemIndexingScope(type="filesystem", directories=["/tmp/status-test"])
        create_run("filesystem", scope)
        run = load_latest_run_by_scope(scope)
        assert run.status in ("pending", "running")

    def test_run_has_source_type_in_list(self, setup_db, api_client):
        run_id = _create_run_via_api(api_client, "/tmp/source-type-test")
        run = _get_run_from_list(api_client, run_id)
        assert run["source_type"] == "filesystem"


class TestRunTransitions:

    def test_start_indexing_returns_200(self, setup_db, api_client):
        run_id = _create_run_via_api(api_client, "/tmp/start-200")
        _start_run(api_client, run_id)

    def test_discovering_stopped_returns_200(self, setup_db, api_client):
        run_id = _create_run_via_api(api_client, "/tmp/disc-stopped")
        _start_run(api_client, run_id)
        resp = api_client.post(f"/runs/discovering_stopped/{run_id}")
        assert resp.status_code == 200

    def test_mark_failed_sets_status_to_failed(self, setup_db, api_client):
        run_id = _create_run_via_api(api_client, "/tmp/mark-failed")
        _start_run(api_client, run_id)
        resp = api_client.post(
            f"/runs/mark_failed/{run_id}",
            json={"error_message": "simulated failure"},
        )
        assert resp.status_code == 200
        run = _get_run_from_list(api_client, run_id)
        assert run is not None
        assert run["status"] == "failed"

    def test_stop_all_does_not_crash(self, setup_db, api_client):
        run_id = _create_run_via_api(api_client, "/tmp/stop-all")
        _start_run(api_client, run_id)
        resp = api_client.post("/runs/stop_all")
        assert resp.status_code == 200


class TestRunList:

    def test_returns_200(self, setup_db, api_client):
        assert api_client.get("/runs/list").status_code == 200

    def test_response_has_runs_key(self, setup_db, api_client):
        body = api_client.get("/runs/list").json()
        assert "runs" in body

    def test_runs_is_a_list(self, setup_db, api_client):
        assert isinstance(api_client.get("/runs/list").json()["runs"], list)

    def test_run_entry_has_required_fields(self, setup_db, api_client):
        run_id = _create_run_via_api(api_client, "/tmp/fields-test")
        run = _get_run_from_list(api_client, run_id)
        assert run is not None
        required = {"run_id", "source_type", "status", "started_at"}
        assert required.issubset(run.keys())

