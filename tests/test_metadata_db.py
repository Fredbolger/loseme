"""
test_metadata_db.py — SQLite metadata layer tests.

All tests use the in-memory db_conn fixture (no disk, no side-effects).
Functions are called directly; DB path is never touched.
"""
import json
import uuid
from datetime import datetime

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.utcnow().isoformat()


def _insert_run(conn, run_id: str, scope_json: dict, status: str = "running",
                source_type: str = "filesystem") -> None:
    now = _now()
    conn.execute(
        """
        INSERT INTO indexing_runs
            (id, celery_task_id, source_type, scope_json, status,
             started_at, updated_at,
             discovered_document_count, indexed_document_count,
             stop_requested, is_discovering, is_indexing)
        VALUES (?, '0', ?, ?, ?, ?, ?, 0, 0, 0, 1, 0)
        """,
        (run_id, source_type, json.dumps(scope_json), status, now, now),
    )
    conn.commit()


def _insert_part(conn, part_id: str, run_id: str, checksum: str = "abc123",
                 scope_json: dict | None = None) -> None:
    if scope_json is None:
        scope_json = {"type": "filesystem", "directories": ["/tmp"]}
    now = _now()
    conn.execute(
        """
        INSERT INTO document_parts
            (document_part_id, checksum, source_type, source_instance_id,
             device_id, source_path, metadata_json, last_indexed_run_id,
             unit_locator, content_type, extractor_name, extractor_version,
             chunker_name, chunker_version, created_at, updated_at, scope_json)
        VALUES (?, ?, 'filesystem', 'sid-1', 'dev-1', '/tmp/f.txt',
                '{}', ?, 'filesystem:/tmp/f.txt', 'text/plain',
                'plaintext', '0.1', 'simple', '1.0', ?, ?, ?)
        """,
        (part_id, checksum, run_id, now, now, json.dumps(scope_json)),
    )
    conn.commit()


# ===========================================================================
# migrations helper
# ===========================================================================

class TestMigrationTable:

    def test_ensure_migration_table_creates_table(self, db_conn):
        from storage.metadata_db.migrations import ensure_migration_table
        ensure_migration_table(db_conn)
        cur = db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        )
        assert cur.fetchone() is not None

    def test_applied_migrations_empty_initially(self, db_conn):
        from storage.metadata_db.migrations import ensure_migration_table, applied_migrations
        ensure_migration_table(db_conn)
        assert applied_migrations(db_conn) == set()

    def test_applied_migrations_records_entry(self, db_conn):
        from storage.metadata_db.migrations import ensure_migration_table, applied_migrations
        ensure_migration_table(db_conn)
        db_conn.execute("INSERT INTO schema_migrations (version) VALUES ('001_test')")
        db_conn.commit()
        assert "001_test" in applied_migrations(db_conn)


# ===========================================================================
# indexing_runs — low-level SQL
# ===========================================================================

class TestIndexingRunsRaw:

    def test_insert_run(self, db_conn):
        rid = str(uuid.uuid4())
        _insert_run(db_conn, rid, {"type": "filesystem", "directories": ["/tmp"]})
        row = db_conn.execute("SELECT id, status FROM indexing_runs WHERE id=?", (rid,)).fetchone()
        assert row is not None
        assert row["status"] == "running"

    def test_update_status(self, db_conn):
        rid = str(uuid.uuid4())
        _insert_run(db_conn, rid, {"type": "filesystem", "directories": ["/tmp"]})
        db_conn.execute(
            "UPDATE indexing_runs SET status=? WHERE id=?", ("completed", rid)
        )
        db_conn.commit()
        row = db_conn.execute("SELECT status FROM indexing_runs WHERE id=?", (rid,)).fetchone()
        assert row["status"] == "completed"

    def test_stop_requested_flag(self, db_conn):
        rid = str(uuid.uuid4())
        _insert_run(db_conn, rid, {"type": "filesystem", "directories": ["/tmp"]})
        db_conn.execute(
            "UPDATE indexing_runs SET stop_requested=1 WHERE id=?", (rid,)
        )
        db_conn.commit()
        row = db_conn.execute(
            "SELECT stop_requested FROM indexing_runs WHERE id=?", (rid,)
        ).fetchone()
        assert bool(row["stop_requested"])

    def test_increment_discovered_count(self, db_conn):
        rid = str(uuid.uuid4())
        _insert_run(db_conn, rid, {"type": "filesystem", "directories": ["/tmp"]})
        db_conn.execute(
            "UPDATE indexing_runs SET discovered_document_count=discovered_document_count+1 WHERE id=?",
            (rid,),
        )
        db_conn.commit()
        row = db_conn.execute(
            "SELECT discovered_document_count FROM indexing_runs WHERE id=?", (rid,)
        ).fetchone()
        assert row["discovered_document_count"] == 1

    def test_increment_indexed_count(self, db_conn):
        rid = str(uuid.uuid4())
        _insert_run(db_conn, rid, {"type": "filesystem", "directories": ["/tmp"]})
        db_conn.execute(
            "UPDATE indexing_runs SET indexed_document_count=indexed_document_count+2 WHERE id=?",
            (rid,),
        )
        db_conn.commit()
        row = db_conn.execute(
            "SELECT indexed_document_count FROM indexing_runs WHERE id=?", (rid,)
        ).fetchone()
        assert row["indexed_document_count"] == 2

    def test_delete_run(self, db_conn):
        rid = str(uuid.uuid4())
        _insert_run(db_conn, rid, {"type": "filesystem", "directories": ["/tmp"]})
        db_conn.execute("DELETE FROM indexing_runs WHERE id=?", (rid,))
        db_conn.commit()
        row = db_conn.execute("SELECT id FROM indexing_runs WHERE id=?", (rid,)).fetchone()
        assert row is None

    def test_is_discovering_default_true(self, db_conn):
        rid = str(uuid.uuid4())
        _insert_run(db_conn, rid, {"type": "filesystem", "directories": ["/tmp"]})
        row = db_conn.execute(
            "SELECT is_discovering FROM indexing_runs WHERE id=?", (rid,)
        ).fetchone()
        assert bool(row["is_discovering"])

    def test_stop_discovery(self, db_conn):
        rid = str(uuid.uuid4())
        _insert_run(db_conn, rid, {"type": "filesystem", "directories": ["/tmp"]})
        db_conn.execute(
            "UPDATE indexing_runs SET is_discovering=0 WHERE id=?", (rid,)
        )
        db_conn.commit()
        row = db_conn.execute(
            "SELECT is_discovering FROM indexing_runs WHERE id=?", (rid,)
        ).fetchone()
        assert not bool(row["is_discovering"])

    def test_show_runs_returns_all(self, db_conn):
        rids = [str(uuid.uuid4()) for _ in range(3)]
        for rid in rids:
            _insert_run(db_conn, rid, {"type": "filesystem", "directories": ["/tmp"]})
        rows = db_conn.execute("SELECT id FROM indexing_runs").fetchall()
        found = {r["id"] for r in rows}
        assert all(rid in found for rid in rids)


# ===========================================================================
# document_parts — low-level SQL
# ===========================================================================

class TestDocumentPartsRaw:

    def test_insert_document_part(self, db_conn):
        rid = str(uuid.uuid4())
        _insert_run(db_conn, rid, {"type": "filesystem", "directories": ["/tmp"]})
        pid = str(uuid.uuid4())
        _insert_part(db_conn, pid, rid)
        row = db_conn.execute(
            "SELECT document_part_id FROM document_parts WHERE document_part_id=?", (pid,)
        ).fetchone()
        assert row is not None

    def test_checksum_stored(self, db_conn):
        rid = str(uuid.uuid4())
        _insert_run(db_conn, rid, {"type": "filesystem", "directories": ["/tmp"]})
        pid = str(uuid.uuid4())
        _insert_part(db_conn, pid, rid, checksum="deadbeef")
        row = db_conn.execute(
            "SELECT checksum FROM document_parts WHERE document_part_id=?", (pid,)
        ).fetchone()
        assert row["checksum"] == "deadbeef"

    def test_mark_processed_updates_chunk_ids(self, db_conn):
        rid = str(uuid.uuid4())
        _insert_run(db_conn, rid, {"type": "filesystem", "directories": ["/tmp"]})
        pid = str(uuid.uuid4())
        _insert_part(db_conn, pid, rid)
        chunk_ids = ["cid1", "cid2"]
        now = _now()
        db_conn.execute(
            """
            UPDATE document_parts
            SET chunk_ids=?, last_indexed_at=?, updated_at=?
            WHERE document_part_id=?
            """,
            (json.dumps(chunk_ids), now, now, pid),
        )
        db_conn.commit()
        row = db_conn.execute(
            "SELECT chunk_ids FROM document_parts WHERE document_part_id=?", (pid,)
        ).fetchone()
        assert json.loads(row["chunk_ids"]) == chunk_ids

    def test_upsert_on_conflict_updates_checksum(self, db_conn):
        rid = str(uuid.uuid4())
        _insert_run(db_conn, rid, {"type": "filesystem", "directories": ["/tmp"]})
        pid = str(uuid.uuid4())
        _insert_part(db_conn, pid, rid, checksum="v1")
        # Simulate upsert with new checksum
        now = _now()
        db_conn.execute(
            """
            INSERT INTO document_parts
                (document_part_id, checksum, source_type, source_instance_id,
                 device_id, source_path, metadata_json, last_indexed_run_id,
                 unit_locator, content_type, extractor_name, extractor_version,
                 chunker_name, chunker_version, created_at, updated_at, scope_json)
            VALUES (?, 'v2', 'filesystem', 'sid-1', 'dev-1', '/tmp/f.txt',
                    '{}', ?, 'filesystem:/tmp/f.txt', 'text/plain',
                    'plaintext', '0.1', 'simple', '1.0', ?, ?, '{}')
            ON CONFLICT(document_part_id) DO UPDATE SET
                checksum = excluded.checksum
            """,
            (pid, rid, now, now),
        )
        db_conn.commit()
        row = db_conn.execute(
            "SELECT checksum FROM document_parts WHERE document_part_id=?", (pid,)
        ).fetchone()
        assert row["checksum"] == "v2"

    def test_delete_document_part(self, db_conn):
        rid = str(uuid.uuid4())
        _insert_run(db_conn, rid, {"type": "filesystem", "directories": ["/tmp"]})
        pid = str(uuid.uuid4())
        _insert_part(db_conn, pid, rid)
        db_conn.execute("DELETE FROM document_parts WHERE document_part_id=?", (pid,))
        db_conn.commit()
        row = db_conn.execute(
            "SELECT document_part_id FROM document_parts WHERE document_part_id=?", (pid,)
        ).fetchone()
        assert row is None

    def test_stale_parts_query(self, db_conn):
        """Parts from a previous run with matching scope are stale in the new run."""
        old_rid = str(uuid.uuid4())
        new_rid = str(uuid.uuid4())
        scope = {"type": "filesystem", "directories": ["/tmp"]}
        _insert_run(db_conn, old_rid, scope)
        _insert_run(db_conn, new_rid, scope)

        stale_pid = str(uuid.uuid4())
        _insert_part(db_conn, stale_pid, old_rid, scope_json=scope)

        # Query mirrors server/storage/metadata_db/document_parts.py get_stale_parts
        scope_json_str = json.dumps(scope)
        rows = db_conn.execute(
            """
            SELECT dp.document_part_id
            FROM document_parts dp
            JOIN indexing_runs ir ON dp.last_indexed_run_id = ir.id
            WHERE ir.scope_json = ? AND dp.last_indexed_run_id != ?
            """,
            (scope_json_str, new_rid),
        ).fetchall()
        found_ids = {r["document_part_id"] for r in rows}
        assert stale_pid in found_ids


# ===========================================================================
# document_parts_queue — low-level SQL
# ===========================================================================

class TestDocumentPartsQueueRaw:

    def _enqueue(self, conn, run_id: str, part_id: str) -> None:
        now = _now()
        conn.execute(
            """
            INSERT INTO document_parts_queue
                (run_id, document_part_id, checksum, source_type,
                 source_instance_id, device_id, source_path, metadata_json,
                 unit_locator, content_type, extractor_name, extractor_version,
                 created_at, updated_at, text, scope_json)
            VALUES (?, ?, 'ck', 'filesystem', 'si', 'dev', '/tmp/f.txt',
                    '{}', 'fs:/tmp/f.txt', 'text/plain', 'plaintext', '0.1',
                    ?, ?, 'hello', '{}')
            """,
            (run_id, part_id, now, now),
        )
        conn.commit()

    def test_enqueue_and_dequeue(self, db_conn):
        rid = str(uuid.uuid4())
        pid = str(uuid.uuid4())
        self._enqueue(db_conn, rid, pid)
        row = db_conn.execute(
            "SELECT document_part_id FROM document_parts_queue WHERE run_id=? ORDER BY created_at LIMIT 1",
            (rid,),
        ).fetchone()
        assert row["document_part_id"] == pid

    def test_remove_from_queue(self, db_conn):
        rid = str(uuid.uuid4())
        pid = str(uuid.uuid4())
        self._enqueue(db_conn, rid, pid)
        db_conn.execute(
            "DELETE FROM document_parts_queue WHERE run_id=? AND document_part_id=?",
            (rid, pid),
        )
        db_conn.commit()
        row = db_conn.execute(
            "SELECT id FROM document_parts_queue WHERE run_id=? AND document_part_id=?",
            (rid, pid),
        ).fetchone()
        assert row is None

    def test_check_if_in_queue(self, db_conn):
        rid = str(uuid.uuid4())
        pid = str(uuid.uuid4())
        self._enqueue(db_conn, rid, pid)
        row = db_conn.execute(
            "SELECT 1 FROM document_parts_queue WHERE run_id=? AND document_part_id=?",
            (rid, pid),
        ).fetchone()
        assert row is not None

    def test_clear_queue_for_run(self, db_conn):
        rid = str(uuid.uuid4())
        for _ in range(3):
            self._enqueue(db_conn, rid, str(uuid.uuid4()))
        db_conn.execute("DELETE FROM document_parts_queue WHERE run_id=?", (rid,))
        db_conn.commit()
        count = db_conn.execute(
            "SELECT COUNT(*) FROM document_parts_queue WHERE run_id=?", (rid,)
        ).fetchone()[0]
        assert count == 0


# ===========================================================================
# monitored_sources — low-level SQL
# ===========================================================================

class TestMonitoredSourcesRaw:

    def _insert_source(self, conn, source_id: str, scope: dict,
                       source_type: str = "filesystem") -> None:
        conn.execute(
            """
            INSERT INTO monitored_sources
                (id, source_type, locator, scope_json, enabled, created_at, device_id)
            VALUES (?, ?, ?, ?, 1, ?, 'dev-1')
            """,
            (source_id, source_type, "fs:/tmp", json.dumps(scope), _now()),
        )
        conn.commit()

    def test_insert_source(self, db_conn):
        sid = str(uuid.uuid4())
        self._insert_source(db_conn, sid, {"type": "filesystem", "directories": ["/tmp"]})
        row = db_conn.execute(
            "SELECT id FROM monitored_sources WHERE id=?", (sid,)
        ).fetchone()
        assert row is not None

    def test_list_all_sources(self, db_conn):
        sids = [str(uuid.uuid4()) for _ in range(3)]
        for i, sid in enumerate(sids):
            self._insert_source(db_conn, sid, {"type": "filesystem", "directories": [f"/d{i}"]})
        rows = db_conn.execute("SELECT id FROM monitored_sources").fetchall()
        found = {r["id"] for r in rows}
        assert all(sid in found for sid in sids)

    def test_delete_source(self, db_conn):
        sid = str(uuid.uuid4())
        self._insert_source(db_conn, sid, {"type": "filesystem", "directories": ["/tmp"]})
        db_conn.execute("DELETE FROM monitored_sources WHERE id=?", (sid,))
        db_conn.commit()
        row = db_conn.execute(
            "SELECT id FROM monitored_sources WHERE id=?", (sid,)
        ).fetchone()
        assert row is None

    def test_update_last_ingested(self, db_conn):
        sid = str(uuid.uuid4())
        self._insert_source(db_conn, sid, {"type": "filesystem", "directories": ["/tmp"]})
        ts = _now()
        db_conn.execute(
            "UPDATE monitored_sources SET last_ingested_at=? WHERE id=?", (ts, sid)
        )
        db_conn.commit()
        row = db_conn.execute(
            "SELECT last_ingested_at FROM monitored_sources WHERE id=?", (sid,)
        ).fetchone()
        assert row["last_ingested_at"] == ts

    def test_scope_json_unique_constraint(self, db_conn):
        """Two sources with the same scope_json must raise IntegrityError."""
        import sqlite3
        scope = json.dumps({"type": "filesystem", "directories": ["/unique"]})
        sid1 = str(uuid.uuid4())
        sid2 = str(uuid.uuid4())
        db_conn.execute(
            "INSERT INTO monitored_sources (id, source_type, locator, scope_json, enabled, created_at, device_id) VALUES (?, 'fs', 'loc', ?, 1, ?, 'dev')",
            (sid1, scope, _now()),
        )
        db_conn.commit()
        with pytest.raises(sqlite3.IntegrityError):
            db_conn.execute(
                "INSERT INTO monitored_sources (id, source_type, locator, scope_json, enabled, created_at, device_id) VALUES (?, 'fs', 'loc', ?, 1, ?, 'dev')",
                (sid2, scope, _now()),
            )
