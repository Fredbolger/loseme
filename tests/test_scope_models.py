"""
test_scope_models.py — IndexingScope serialization / deserialization.

Validates that round-tripping scope objects through serialize/deserialize
is lossless and that locators are stable.
"""
from pathlib import Path

import pytest


# ===========================================================================
# FilesystemIndexingScope
# ===========================================================================

class TestFilesystemIndexingScope:

    @pytest.fixture
    def scope_cls(self):
        from loseme_core.filesystem_model import FilesystemIndexingScope
        return FilesystemIndexingScope

    def test_serialize_contains_type(self, scope_cls):
        scope = scope_cls(directories=[Path("/tmp/docs")])
        d = scope.serialize()
        assert d["type"] == "filesystem"

    def test_serialize_contains_directories(self, scope_cls):
        scope = scope_cls(directories=[Path("/tmp/docs"), Path("/tmp/notes")])
        d = scope.serialize()
        assert "/tmp/docs" in d["directories"]
        assert "/tmp/notes" in d["directories"]

    def test_serialize_contains_recursive(self, scope_cls):
        scope = scope_cls(directories=[Path("/tmp")], recursive=False)
        assert scope.serialize()["recursive"] is False

    def test_serialize_include_patterns(self, scope_cls):
        scope = scope_cls(directories=[Path("/tmp")], include_patterns=["*.md"])
        assert "*.md" in scope.serialize()["include_patterns"]

    def test_serialize_exclude_patterns(self, scope_cls):
        scope = scope_cls(directories=[Path("/tmp")], exclude_patterns=["*.log"])
        assert "*.log" in scope.serialize()["exclude_patterns"]

    def test_deserialize_round_trip(self, scope_cls):
        original = scope_cls(
            directories=[Path("/tmp/docs")],
            recursive=True,
            include_patterns=["*.txt"],
            exclude_patterns=["*.bak"],
        )
        restored = scope_cls.deserialize(original.serialize())
        assert [str(p) for p in restored.directories] == [str(p) for p in original.directories]
        assert restored.recursive == original.recursive
        assert restored.include_patterns == original.include_patterns
        assert restored.exclude_patterns == original.exclude_patterns

    def test_locator_is_stable(self, scope_cls):
        scope = scope_cls(directories=[Path("/tmp/docs")])
        assert scope.locator() == scope.locator()

    def test_locator_contains_directories(self, scope_cls):
        scope = scope_cls(directories=[Path("/tmp/docs")])
        assert "/tmp/docs" in scope.locator()

    def test_locator_differs_for_different_dirs(self, scope_cls):
        a = scope_cls(directories=[Path("/tmp/a")]).locator()
        b = scope_cls(directories=[Path("/tmp/b")]).locator()
        assert a != b

    def test_deserialize_rejects_single_char_path(self, scope_cls):
        with pytest.raises(ValueError):
            scope_cls.deserialize({"type": "filesystem", "directories": ["/"]})

    def test_type_field_is_filesystem(self, scope_cls):
        scope = scope_cls(directories=[Path("/tmp")])
        assert scope.type == "filesystem"


# ===========================================================================
# ThunderbirdIndexingScope
# ===========================================================================

class TestThunderbirdIndexingScope:

    @pytest.fixture
    def scope_cls(self):
        from loseme_core.thunderbird_model import ThunderbirdIndexingScope
        return ThunderbirdIndexingScope

    def test_serialize_contains_type(self, scope_cls):
        scope = scope_cls(mbox_path="/mail/Inbox")
        assert scope.serialize()["type"] == "thunderbird"

    def test_serialize_contains_mbox_path(self, scope_cls):
        scope = scope_cls(mbox_path="/mail/Inbox")
        assert scope.serialize()["mbox_path"] == "/mail/Inbox"

    def test_serialize_contains_ignore_patterns(self, scope_cls):
        patterns = [{"field": "from", "value": "spam@example.com"}]
        scope = scope_cls(mbox_path="/mail/Inbox", ignore_patterns=patterns)
        assert scope.serialize()["ignore_patterns"] == patterns

    def test_deserialize_round_trip(self, scope_cls):
        original = scope_cls(
            mbox_path="/mail/Inbox",
            ignore_patterns=[{"field": "from", "value": "noreply@example.com"}],
        )
        restored = scope_cls.deserialize(original.serialize())
        assert restored.mbox_path == original.mbox_path
        assert restored.ignore_patterns == original.ignore_patterns

    def test_locator_is_mbox_path(self, scope_cls):
        scope = scope_cls(mbox_path="/mail/Inbox")
        assert scope.locator() == "/mail/Inbox"

    def test_type_field_is_thunderbird(self, scope_cls):
        scope = scope_cls(mbox_path="/mail/Inbox")
        assert scope.type == "thunderbird"

    def test_no_ignore_patterns_default_none(self, scope_cls):
        scope = scope_cls(mbox_path="/mail/Inbox")
        assert scope.ignore_patterns is None


# ===========================================================================
# IndexingScope.deserialize (polymorphic dispatch)
# ===========================================================================

class TestIndexingScopeDeserialize:

    def test_deserialize_filesystem(self):
        from loseme_core.scope_models import IndexingScope
        from loseme_core.filesystem_model import FilesystemIndexingScope
        data = {
            "type": "filesystem",
            "directories": ["/tmp/docs"],
            "recursive": True,
            "include_patterns": [],
            "exclude_patterns": [],
        }
        scope = IndexingScope.deserialize(data)
        assert isinstance(scope, FilesystemIndexingScope)

    def test_deserialize_thunderbird(self):
        from loseme_core.scope_models import IndexingScope
        from loseme_core.thunderbird_model import ThunderbirdIndexingScope
        data = {"type": "thunderbird", "mbox_path": "/mail/Inbox"}
        scope = IndexingScope.deserialize(data)
        assert isinstance(scope, ThunderbirdIndexingScope)

    def test_deserialize_unknown_type_raises(self):
        from loseme_core.scope_models import IndexingScope
        with pytest.raises((ValueError, KeyError)):
            IndexingScope.deserialize({"type": "unknown"})


# ===========================================================================
# StoredScope (server-side)
# ===========================================================================

class TestStoredScope:

    def test_stored_scope_allows_extra_fields(self):
        from storage.metadata_db.models import StoredScope
        scope = StoredScope(type="filesystem", extra_field="allowed")
        assert scope.type == "filesystem"

    def test_stored_scope_locator_returns_type(self):
        from storage.metadata_db.models import StoredScope
        scope = StoredScope(type="thunderbird")
        assert scope.locator() == "thunderbird"

    def test_stored_scope_serialize_round_trips(self):
        from storage.metadata_db.models import StoredScope
        scope = StoredScope(type="filesystem", directories=["/tmp"])
        d = scope.serialize()
        assert d["type"] == "filesystem"
