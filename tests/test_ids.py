"""
test_ids.py — ID stability tests.

Deduplication, skip-on-reingest, and stale-vector cleanup all depend on IDs
being perfectly deterministic.  A regression here silently double-indexes
every document without surfacing any error.
"""
from pathlib import Path

import pytest

from loseme_core.ids import (
    make_chunk_id,
    make_logical_document_part_id,
    make_source_instance_id,
    make_thunderbird_source_id,
)


# ===========================================================================
# make_source_instance_id
# ===========================================================================

class TestSourceInstanceId:

    def test_deterministic(self):
        a = make_source_instance_id("filesystem", "dev1", Path("/home/user/docs"))
        b = make_source_instance_id("filesystem", "dev1", Path("/home/user/docs"))
        assert a == b

    def test_differs_by_device(self):
        a = make_source_instance_id("filesystem", "mac", Path("/docs"))
        b = make_source_instance_id("filesystem", "linux", Path("/docs"))
        assert a != b

    def test_differs_by_path(self):
        a = make_source_instance_id("filesystem", "dev1", Path("/home/alice"))
        b = make_source_instance_id("filesystem", "dev1", Path("/home/bob"))
        assert a != b

    def test_differs_by_source_type(self):
        a = make_source_instance_id("filesystem", "dev1", Path("/data"))
        b = make_source_instance_id("thunderbird", "dev1", Path("/data"))
        assert a != b

    def test_returns_hex_string(self):
        sid = make_source_instance_id("filesystem", "dev1", Path("/docs"))
        assert isinstance(sid, str)
        assert all(c in "0123456789abcdef" for c in sid)
        assert len(sid) == 64  # SHA-256 hex

    def test_symlink_resolves_same(self, tmp_path):
        real = tmp_path / "real.txt"
        real.write_text("content")
        link = tmp_path / "link.txt"
        link.symlink_to(real)
        a = make_source_instance_id("filesystem", "dev1", real.resolve())
        b = make_source_instance_id("filesystem", "dev1", link.resolve())
        assert a == b

    def test_trailing_slash_invariant(self):
        """Path normalisation must handle trailing slashes."""
        a = make_source_instance_id("filesystem", "dev1", Path("/docs/"))
        b = make_source_instance_id("filesystem", "dev1", Path("/docs"))
        # Both resolve() to the same canonical path
        assert a == b


# ===========================================================================
# make_logical_document_part_id
# ===========================================================================

class TestLogicalDocumentPartId:

    def _sid(self):
        return make_source_instance_id("filesystem", "dev1", Path("/docs"))

    def test_deterministic(self):
        sid = self._sid()
        a = make_logical_document_part_id(sid, "filesystem:/docs/file.txt")
        b = make_logical_document_part_id(sid, "filesystem:/docs/file.txt")
        assert a == b

    def test_differs_by_locator(self):
        sid = self._sid()
        a = make_logical_document_part_id(sid, "filesystem:/docs/a.txt")
        b = make_logical_document_part_id(sid, "filesystem:/docs/b.txt")
        assert a != b

    def test_differs_by_source_instance(self):
        sid1 = make_source_instance_id("filesystem", "dev1", Path("/docs"))
        sid2 = make_source_instance_id("filesystem", "dev2", Path("/docs"))
        loc = "filesystem:/docs/file.txt"
        assert make_logical_document_part_id(sid1, loc) != make_logical_document_part_id(sid2, loc)

    def test_returns_32_char_hex(self):
        sid = self._sid()
        doc_id = make_logical_document_part_id(sid, "filesystem:/docs/file.txt")
        assert isinstance(doc_id, str)
        assert len(doc_id) == 32
        assert all(c in "0123456789abcdef" for c in doc_id)

    def test_cross_device_produces_different_ids(self):
        """Same logical path on two devices → different IDs (current design)."""
        loc = "filesystem:/shared/report.pdf"
        sid_a = make_source_instance_id("filesystem", "mac", Path("/shared"))
        sid_b = make_source_instance_id("filesystem", "linux", Path("/shared"))
        assert make_logical_document_part_id(sid_a, loc) != make_logical_document_part_id(sid_b, loc)


# ===========================================================================
# make_chunk_id
# ===========================================================================

class TestChunkId:

    def _doc_id(self):
        sid = make_source_instance_id("filesystem", "dev1", Path("/docs"))
        return make_logical_document_part_id(sid, "filesystem:/docs/f.txt")

    def test_deterministic(self):
        doc_id = self._doc_id()
        assert make_chunk_id(doc_id, "abc123", 0) == make_chunk_id(doc_id, "abc123", 0)

    def test_differs_by_checksum(self):
        doc_id = self._doc_id()
        assert make_chunk_id(doc_id, "v1", 0) != make_chunk_id(doc_id, "v2", 0)

    def test_differs_by_index(self):
        doc_id = self._doc_id()
        assert make_chunk_id(doc_id, "ck", 0) != make_chunk_id(doc_id, "ck", 1)

    def test_differs_by_document_part_id(self):
        sid = make_source_instance_id("filesystem", "dev1", Path("/docs"))
        doc_a = make_logical_document_part_id(sid, "filesystem:/docs/a.txt")
        doc_b = make_logical_document_part_id(sid, "filesystem:/docs/b.txt")
        assert make_chunk_id(doc_a, "ck", 0) != make_chunk_id(doc_b, "ck", 0)

    def test_returns_hex_string(self):
        cid = make_chunk_id(self._doc_id(), "ck", 0)
        assert isinstance(cid, str)
        assert all(c in "0123456789abcdef" for c in cid)


# ===========================================================================
# make_thunderbird_source_id
# ===========================================================================

class TestThunderbirdSourceId:

    def test_deterministic(self):
        a = make_thunderbird_source_id("dev1", "/mail/Inbox", "<msg1@host>")
        b = make_thunderbird_source_id("dev1", "/mail/Inbox", "<msg1@host>")
        assert a == b

    def test_differs_by_message_id(self):
        a = make_thunderbird_source_id("dev1", "/mail/Inbox", "<msg1@host>")
        b = make_thunderbird_source_id("dev1", "/mail/Inbox", "<msg2@host>")
        assert a != b

    def test_differs_by_mbox_path(self):
        a = make_thunderbird_source_id("dev1", "/mail/Inbox", "<msg@host>")
        b = make_thunderbird_source_id("dev1", "/mail/Sent", "<msg@host>")
        assert a != b

    def test_differs_by_device(self):
        a = make_thunderbird_source_id("dev1", "/mail/Inbox", "<msg@host>")
        b = make_thunderbird_source_id("dev2", "/mail/Inbox", "<msg@host>")
        assert a != b
