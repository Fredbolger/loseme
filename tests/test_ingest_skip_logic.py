"""
Ingest skip-logic tests.

Documents that haven't changed must not be re-processed.
Documents whose checksum or extractor version has changed must be re-processed.

A regression here either wastes compute on every indexing run, or —
worse — silently loses updates when files are edited.
"""

from unittest.mock import MagicMock, patch

import pytest

from tests.helpers import client, create_filesystem_run, ingest_part, make_part


@pytest.fixture(autouse=True)
def mock_vector_store():
    """Replace the vector store with a no-op mock for all tests in this module."""
    with patch("storage.vector_db.runtime.get_vector_store") as mock:
        instance = MagicMock()
        instance.search.return_value = []
        mock.return_value = instance
        yield instance


class TestSkipUnchangedDocument:

    def test_unchanged_document_is_skipped_on_second_ingest(self, setup_db):
        part = make_part()

        first = ingest_part(part, create_filesystem_run())
        assert first.get("accepted") is True

        second = ingest_part(part, create_filesystem_run())
        assert second.get("skipped") is True, (
            "An unchanged document must be skipped on re-ingest"
        )

    def test_skipped_document_does_not_hit_vector_store(self, setup_db, mock_vector_store):
        part = make_part()
        ingest_part(part, create_filesystem_run())
        mock_vector_store.add.reset_mock()

        ingest_part(part, create_filesystem_run())

        mock_vector_store.add.assert_not_called()


class TestReprocessOnChange:

    def test_changed_checksum_triggers_reprocess(self, setup_db):
        original = make_part(text="original content")
        ingest_part(original, create_filesystem_run())

        updated = make_part(text="updated content").model_copy(
            update={"document_part_id": original.document_part_id}
        )
        result = ingest_part(updated, create_filesystem_run())

        assert result.get("skipped") is not True, (
            "A changed checksum must trigger re-processing"
        )

    def test_changed_extractor_version_triggers_reprocess(self, setup_db):
        part = make_part()
        ingest_part(part, create_filesystem_run())

        upgraded = part.model_copy(update={"extractor_version": "2.0"})
        result = ingest_part(upgraded, create_filesystem_run())

        assert result.get("skipped") is not True, (
            "A changed extractor version must trigger re-processing"
        )

    def test_changed_extractor_name_triggers_reprocess(self, setup_db):
        part = make_part()
        ingest_part(part, create_filesystem_run())

        rextracted = part.model_copy(update={"extractor_name": "new_extractor"})
        result = ingest_part(rextracted, create_filesystem_run())

        assert result.get("skipped") is not True, (
            "A changed extractor name must trigger re-processing"
        )
