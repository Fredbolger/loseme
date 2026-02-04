import pytest
from storage.metadata_db.db import init_db
from storage.vector_db.runtime import get_vector_store
from storage.metadata_db.db import delete_database
import mailbox
import email.utils
from email.message import EmailMessage
from pathlib import Path

def clear_all():
    vector_store = get_vector_store()
    vector_store.delete_collection()
    delete_database()


@pytest.fixture
def setup_db():
    """
    Initialize a fresh database for testing.
    """
    
    # We need to patch the DB_PATH in storage.metadata_db.db to use a different path for tests
    with pytest.MonkeyPatch.context() as m:
        test_db_path = Path("./test_metadata.db")
        m.setattr("storage.metadata_db.db.DB_PATH", test_db_path)
        init_db()
    yield
    clear_all()
    if test_db_path.exists():
        # Clean up test database file
        test_db_path.unlink()

@pytest.fixture
def set_embedding_model_env(monkeypatch):
    monkeypatch.setenv("EMBEDDING_MODEL", "bge-m3")
    return "EMBEDDING_MODEL"

@pytest.fixture
def fake_mbox_path(tmp_path: Path) -> str:
    """
    Creates a small deterministic Thunderbird-style mbox file.


    - ~20 messages
    - some senders from google.com (for ignore-pattern tests)
    - stable Message-IDs
    """
    mbox_dir = tmp_path / "thunderbird"
    mbox_dir.mkdir()


    mbox_path = mbox_dir / "INBOX"
    mbox = mailbox.mbox(mbox_path)


    for i in range(20):
        msg = EmailMessage()
        sender = (
        f"user{i}@google.com" if i % 3 == 0 else f"user{i}@example.com"
        )
        msg["From"] = sender
        msg["To"] = "me@example.com"
        msg["Subject"] = f"Test message {i}"
        msg["Date"] = email.utils.formatdate(localtime=True)
        msg["Message-ID"] = f"<test-{i}@example.com>"
        msg.set_content(f"This is the body of message {i}")


        mbox.add(msg)


    mbox.flush()
    mbox.close()


    return str(mbox_path)
