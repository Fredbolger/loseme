"""
ID stability tests.

The entire deduplication strategy — skip-on-reingest, cross-device dedup,
old-vector cleanup — rests on IDs being deterministic. A regression here
silently double-indexes every document without any visible error.
"""

from pathlib import Path

from src.core.ids import (
    make_chunk_id,
    make_logical_document_part_id,
    make_source_instance_id,
)


class TestSourceInstanceId:

    def test_is_deterministic(self):
        a = make_source_instance_id("filesystem", "dev1", Path("/home/user/docs"))
        b = make_source_instance_id("filesystem", "dev1", Path("/home/user/docs"))
        assert a == b, "Same inputs must always produce the same source_instance_id"

    def test_differs_by_device(self):
        a = make_source_instance_id("filesystem", "mac-pro", Path("/home/user/docs"))
        b = make_source_instance_id("filesystem", "linux-box", Path("/home/user/docs"))
        assert a != b, "Different devices must produce different source_instance_ids"

    def test_differs_by_path(self):
        a = make_source_instance_id("filesystem", "dev1", Path("/home/alice/docs"))
        b = make_source_instance_id("filesystem", "dev1", Path("/home/bob/docs"))
        assert a != b

    def test_differs_by_source_type(self):
        a = make_source_instance_id("filesystem", "dev1", Path("/data"))
        b = make_source_instance_id("thunderbird", "dev1", Path("/data"))
        assert a != b

    def test_symlink_resolves_to_same_id(self, tmp_path):
        """Indexing a symlink and its target must yield identical IDs."""
        real = tmp_path / "real.txt"
        real.write_text("content")
        link = tmp_path / "link.txt"
        link.symlink_to(real)

        a = make_source_instance_id("filesystem", "dev1", real.resolve())
        b = make_source_instance_id("filesystem", "dev1", link.resolve())
        assert a == b, "Symlinks must resolve to the same source_instance_id"


class TestLogicalDocumentPartId:

    def test_is_deterministic(self):
        sid = make_source_instance_id("filesystem", "dev1", Path("/docs"))
        a = make_logical_document_part_id(sid, "filesystem:/docs/file.txt")
        b = make_logical_document_part_id(sid, "filesystem:/docs/file.txt")
        assert a == b

    def test_differs_by_unit_locator(self):
        sid = make_source_instance_id("filesystem", "dev1", Path("/docs"))
        a = make_logical_document_part_id(sid, "filesystem:/docs/a.txt")
        b = make_logical_document_part_id(sid, "filesystem:/docs/b.txt")
        assert a != b

    def test_differs_by_source_instance(self):
        sid1 = make_source_instance_id("filesystem", "dev1", Path("/docs"))
        sid2 = make_source_instance_id("filesystem", "dev2", Path("/docs"))
        locator = "filesystem:/docs/file.txt"
        assert make_logical_document_part_id(sid1, locator) != make_logical_document_part_id(sid2, locator)

    def test_result_is_32_char_hex_string(self):
        sid = make_source_instance_id("filesystem", "dev1", Path("/docs"))
        doc_id = make_logical_document_part_id(sid, "filesystem:/docs/file.txt")
        assert isinstance(doc_id, str)
        assert len(doc_id) == 32
        assert all(c in "0123456789abcdef" for c in doc_id)

    def test_cross_device_dedup_behaviour_is_documented(self):
        """
        Documents at the same logical path on two different devices produce
        DIFFERENT logical IDs because the source_instance_id differs.

        This test pins the current behaviour. If cross-device dedup is ever
        implemented (same logical path → same ID regardless of device),
        update this assertion accordingly.
        """
        unit_locator = "filesystem:/shared/report.pdf"
        sid_mac = make_source_instance_id("filesystem", "mac", Path("/shared"))
        sid_linux = make_source_instance_id("filesystem", "linux", Path("/shared"))

        id_mac = make_logical_document_part_id(sid_mac, unit_locator)
        id_linux = make_logical_document_part_id(sid_linux, unit_locator)

        # Currently differ — each device has its own embeddings.
        assert id_mac != id_linux


class TestChunkId:

    def _doc_id(self) -> str:
        sid = make_source_instance_id("filesystem", "dev1", Path("/docs"))
        return make_logical_document_part_id(sid, "filesystem:/docs/f.txt")

    def test_is_deterministic(self):
        doc_id = self._doc_id()
        assert make_chunk_id(doc_id, "abc", 0) == make_chunk_id(doc_id, "abc", 0)

    def test_changes_with_checksum(self):
        """A file edit must produce new chunk IDs so stale vectors are replaced."""
        doc_id = self._doc_id()
        assert make_chunk_id(doc_id, "checksum-v1", 0) != make_chunk_id(doc_id, "checksum-v2", 0)

    def test_changes_with_index(self):
        doc_id = self._doc_id()
        assert make_chunk_id(doc_id, "same", 0) != make_chunk_id(doc_id, "same", 1)

    def test_changes_with_document_part_id(self):
        sid = make_source_instance_id("filesystem", "dev1", Path("/docs"))
        doc_a = make_logical_document_part_id(sid, "filesystem:/docs/a.txt")
        doc_b = make_logical_document_part_id(sid, "filesystem:/docs/b.txt")
        assert make_chunk_id(doc_a, "ck", 0) != make_chunk_id(doc_b, "ck", 0)
