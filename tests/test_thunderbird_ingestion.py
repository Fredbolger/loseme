import pytest
import sys
import logging

logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(name)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

logger = logging.getLogger(__name__)

# Mute logging from urllib3 used by some email libraries
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("transformers_modules").setLevel(logging.WARNING)

from src.domain.models import EmailDocument, ThunderbirdIndexingScope
from collectors.thunderbird.thunderbird_source import ThunderbirdIngestionSource
from api.app.services.ingestion import ingest_scope, IngestionCancelled
from storage.metadata_db.indexing_runs import create_run
from storage.metadata_db.processed_documents import get_all_processed
from storage.metadata_db.db import delete_database

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
    

def test_thunderbird_source_type():
    mbox_path = "/app/data/email/INBOX"
    scope = ThunderbirdIndexingScope(type ="thunderbird", mbox_path=mbox_path)
    assert scope.type == "thunderbird"
    assert scope.mbox_path == mbox_path

    source = ThunderbirdIngestionSource(scope=scope, should_stop=lambda: False)
    assert source.scope.type == "thunderbird"
    
    idx = 0
    for email in source.iter_documents():
        logger.info(f"Email {idx}: source_id={email.source_id}, subject={email.metadata.get('subject')}")
        assert email.text is not None
        if idx >= 2:
            break
        idx += 1
    
    assert idx > 0

def test_thunderbird_ignore_pattern():
    mbox_path = "/app/data/email/INBOX"
    ignore_patterns = [{"field": "from", "value":"*google.com*"}]
    scope_with_ignore = ThunderbirdIndexingScope(type ="thunderbird", mbox_path=mbox_path, ignore_patterns=ignore_patterns)
    scope_without_ignore = ThunderbirdIndexingScope(type ="thunderbird", mbox_path=mbox_path)

    source_with_ignore = ThunderbirdIngestionSource(scope=scope_with_ignore, should_stop=lambda: False)
    source_without_ignore = ThunderbirdIngestionSource(scope=scope_without_ignore, should_stop=lambda: False)
    
    idx_with_ignore = 0
    # make sure the results differ if email.metadata['from'] matches the ignore pattern
    for email_ignored, email_not_ignored in zip(source_with_ignore.iter_documents(), source_without_ignore.iter_documents()):
        from_value = email_not_ignored.metadata.get('from', '')
        if from_value is None:
            from_value = ''
        pattern = ignore_patterns[0]['value'].strip('*')
        if pattern in from_value:
            idx_with_ignore += 1
            # Make sure the texts of the discovered emails differ
            assert email_ignored.text != email_not_ignored.text
        else:
            if email_ignored.source_id == email_not_ignored.source_id:
                assert email_ignored.text == email_not_ignored.text
        
        if idx_with_ignore >= 2:
            break

def test_thunderbird_ingestion_service(setup_db):
    scope = ThunderbirdIndexingScope(
        type="thunderbird",
        mbox_path="/app/data/email/INBOX"
    )

    run = create_run("thunderbird", scope)
    logger.info(f"Created run: {run}")
    
    ingestion_result = ingest_scope(scope, run.id, resume=False, stop_after=5)
    assert ingestion_result.status == "interrupted"
    assert ingestion_result.documents_indexed == 5
    
    # Resume run
    ingestion_result2 = ingest_scope(scope, run.id, resume=True, stop_after=10)
    assert ingestion_result2.documents_indexed == 10

    # We should now have discovered a total of 15 documents
    # (5 from the first run, 10 from the resumed run)
    # query all processed documents from the db
    all_processed = get_all_processed(run.id)
    
    logger.info(f"Proccesed documents are:\n{all_processed}")
    assert len(all_processed) == 15

if __name__ == "__main__":
    test_email_document_constructor_sets_thunderbird_ids()
    test_thunderbird_source_type()
    test_thunderbird_ignore_pattern()
    from conftest import *
    init_db()
    test_thunderbird_ingestion_service(None)
    clear_all()
