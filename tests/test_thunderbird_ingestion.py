import pytest
from src.domain.models import EmailDocument

def test_email_document_constructor_sets_thunderbird_ids():
    doc = EmailDocument(
        id="doc-1",
        source_type="thunderbird",
        device_id="test-device",
        mbox_path="/home/user/.thunderbird/Inbox",
        message_id="<abc123@example.com>",
        text="Hello world",
        checksum="checksum-1",
        metadata={},
    )

    # core invariants
    assert doc.source_type == "thunderbird"
    assert doc.device_id == "test-device"
    assert doc.mbox_path.endswith("Inbox")
    assert doc.message_id == "<abc123@example.com>"
    assert doc.text == "Hello world"

    # thunderbird-specific identity
    assert doc.source_id is not None
    assert doc.source_id != ""
    assert doc.source_path == "Inbox/<abc123@example.com>"

