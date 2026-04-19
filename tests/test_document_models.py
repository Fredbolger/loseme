"""
test_document_models.py — Pydantic model validation for core domain models.

No I/O, no network, pure Python.
"""
import hashlib
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from loseme_core.document_models import DocumentPart, Document, Chunk
from loseme_core.ids import make_logical_document_part_id, make_source_instance_id


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sid():
    return make_source_instance_id("filesystem", "dev1", Path("/tmp"))


def _doc_id():
    return make_logical_document_part_id(_sid(), "filesystem:/tmp/doc.txt")


def _make_part(**kwargs):
    defaults = dict(
        text="hello world",
        document_part_id=_doc_id(),
        checksum=hashlib.sha256(b"hello world").hexdigest(),
        source_type="filesystem",
        source_instance_id=_sid(),
        device_id="dev1",
        source_path="/tmp/doc.txt",
        unit_locator="filesystem:/tmp/doc.txt",
        content_type="text/plain",
        extractor_name="plaintext",
        extractor_version="0.1",
        scope_json={"type": "filesystem", "directories": ["/tmp"]},
    )
    defaults.update(kwargs)
    return DocumentPart(**defaults)


def _make_document(**kwargs):
    defaults = dict(
        id=_doc_id(),
        source_type="filesystem",
        source_id=_sid(),
        device_id="dev1",
        source_path="/tmp/doc.txt",
        checksum=hashlib.sha256(b"content").hexdigest(),
    )
    defaults.update(kwargs)
    return Document(**defaults)


# ===========================================================================
# DocumentPart
# ===========================================================================

class TestDocumentPart:

    def test_valid_part_created(self):
        part = _make_part()
        assert part.document_part_id == _doc_id()

    def test_text_field_optional(self):
        part = _make_part(text=None)
        assert part.text is None

    def test_metadata_json_defaults_to_empty_dict(self):
        part = _make_part()
        assert part.metadata_json == {}

    def test_created_at_defaults_to_now(self):
        part = _make_part()
        assert isinstance(part.created_at, datetime)

    def test_updated_at_defaults_to_now(self):
        part = _make_part()
        assert isinstance(part.updated_at, datetime)

    def test_scope_json_must_be_dict(self):
        with pytest.raises((ValidationError, ValueError)):
            _make_part(scope_json="not a dict")

    def test_scope_json_stored_correctly(self):
        scope = {"type": "filesystem", "directories": ["/tmp"]}
        part = _make_part(scope_json=scope)
        assert part.scope_json == scope

    def test_invalid_metadata_json_type_raises(self):
        """metadata_json field must accept None gracefully but not crash."""
        part = _make_part(metadata_json=None)
        assert part.metadata_json is None

    def test_all_required_fields_present(self):
        part = _make_part()
        required = [
            "document_part_id", "checksum", "source_type",
            "source_instance_id", "device_id", "source_path",
            "unit_locator", "content_type", "extractor_name",
            "extractor_version",
        ]
        for field in required:
            assert getattr(part, field) is not None


# ===========================================================================
# Document
# ===========================================================================

class TestDocument:

    def test_valid_document_created(self):
        doc = _make_document()
        assert doc.id == _doc_id()

    def test_empty_id_raises(self):
        with pytest.raises(ValidationError):
            _make_document(id="")

    def test_empty_checksum_raises(self):
        with pytest.raises(ValidationError):
            _make_document(checksum="")

    def test_invalid_source_type_raises(self):
        with pytest.raises(ValidationError):
            _make_document(source_type="unknown_type")

    def test_valid_source_types(self):
        for st in ("filesystem", "thunderbird"):
            doc = _make_document(source_type=st)
            assert doc.source_type == st

    def test_empty_source_path_raises(self):
        with pytest.raises(ValidationError):
            _make_document(source_path="")

    def test_empty_device_id_raises(self):
        with pytest.raises(ValidationError):
            _make_document(device_id="")

    def test_parts_default_empty_list(self):
        doc = _make_document()
        assert doc.parts == []

    def test_add_part(self):
        doc = _make_document()
        part = _make_part()
        doc.add_part(part)
        assert len(doc.parts) == 1
        assert doc.parts[0].document_part_id == part.document_part_id

    def test_add_multiple_parts(self):
        doc = _make_document()
        for i in range(3):
            sid = make_source_instance_id("filesystem", "dev1", Path("/tmp"))
            doc_id = make_logical_document_part_id(sid, f"filesystem:/tmp/doc{i}.txt")
            part = _make_part(
                document_part_id=doc_id,
                unit_locator=f"filesystem:/tmp/doc{i}.txt",
            )
            doc.add_part(part)
        assert len(doc.parts) == 3

    def test_metadata_defaults_empty_dict(self):
        doc = _make_document()
        assert doc.metadata == {}

    def test_to_dict_source_path_is_string(self):
        doc = _make_document()
        d = doc.to_dict()
        assert isinstance(d["source_path"], str)

    def test_source_id_auto_generated_if_missing(self):
        """source_id is auto-generated from source_type + device_id + source_path."""
        doc = Document(
            id=_doc_id(),
            source_type="filesystem",
            device_id="dev1",
            source_path="/tmp/doc.txt",
            checksum="ck",
        )
        assert doc.source_id is not None
        assert len(doc.source_id) > 0


# ===========================================================================
# Chunk
# ===========================================================================

class TestChunk:

    def _make_chunk(self, **kwargs):
        from loseme_core.ids import make_chunk_id
        doc_id = _doc_id()
        cid = make_chunk_id(doc_id, "ck", 0)
        defaults = dict(
            id=cid,
            source_type="filesystem",
            source_path="/tmp/doc.txt",
            text="chunk text",
            document_part_id=doc_id,
            device_id="dev1",
            unit_locator="filesystem:/tmp/doc.txt",
            index=0,
            metadata={"char_len": 10},
        )
        defaults.update(kwargs)
        return Chunk(**defaults)

    def test_valid_chunk_created(self):
        chunk = self._make_chunk()
        assert chunk.index == 0

    def test_empty_id_raises(self):
        with pytest.raises(ValidationError):
            self._make_chunk(id="")

    def test_empty_document_part_id_raises(self):
        with pytest.raises(ValidationError):
            self._make_chunk(document_part_id="")

    def test_empty_device_id_raises(self):
        with pytest.raises(ValidationError):
            self._make_chunk(device_id="")

    def test_negative_index_raises(self):
        with pytest.raises(ValidationError):
            self._make_chunk(index=-1)

    def test_zero_index_valid(self):
        chunk = self._make_chunk(index=0)
        assert chunk.index == 0

    def test_metadata_defaults_empty_dict(self):
        chunk = self._make_chunk(metadata={})
        assert chunk.metadata == {}

    def test_text_optional(self):
        chunk = self._make_chunk(text=None)
        assert chunk.text is None

    def test_metadata_stored(self):
        chunk = self._make_chunk(metadata={"char_len": 42})
        assert chunk.metadata["char_len"] == 42
