import pytest
from storage.metadata_db.db import init_db
from storage.vector_db.runtime import get_vector_store
from storage.metadata_db.db import delete_database
import mailbox
import email.utils
from email.message import EmailMessage
from pathlib import Path
from fastapi.testclient import TestClient
from api.app.main import app
import pypdf

import logging

# Write logs to "pytest.log" file
logging.getLogger().addHandler(logging.FileHandler("pytest.log"))


def clear_all():
    vector_store = get_vector_store()
    vector_store.delete_collection()
    delete_database()

@pytest.fixture
def setup_db(tmp_path):
    """
    Initialize a fresh database for testing.
    """
    # Clear any existing data before starting the test
    clear_all()

    # We need to patch the DB_PATH in storage.metadata_db.db to use a different path for tests
    with pytest.MonkeyPatch.context() as m:
        test_db_path = tmp_path / "test_metadata.db"
        pytest.MonkeyPatch().setattr("storage.metadata_db.db.DB_PATH", test_db_path)
        m.setattr("storage.metadata_db.db.DB_PATH", test_db_path)
        init_db()
    yield test_db_path
    clear_all()
    if test_db_path.exists():
        # Clean up test database file
        test_db_path.unlink()

@pytest.fixture
def set_embedding_model_env(monkeypatch):
    monkeypatch.setenv("EMBEDDING_MODEL", "bge-m3")
    return "EMBEDDING_MODEL"

@pytest.fixture(autouse=False)
def fake_loseme_paths(tmp_path, monkeypatch):
    fake_data_dir = tmp_path
    fake_host_root = tmp_path

    monkeypatch.setattr(
        "src.sources.filesystem.filesystem_source.LOSEME_DATA_DIR",
        fake_data_dir,
    )
    monkeypatch.setattr(
        "src.sources.filesystem.filesystem_source.LOSEME_SOURCE_ROOT_HOST",
        fake_host_root,
    )



@pytest.fixture
def write_files_to_disk(tmp_path: Path) -> Path:
    """
    Fixture to create a temporary directory with some files for testing.
    """
    test_dir = tmp_path / "test_files"
    test_dir.mkdir()

    # Create some test files
    (test_dir / "file1.txt").write_text("This is the content of file 1.")
    (test_dir / "IgnorePath").mkdir()
    (test_dir / "IgnorePath" / "file2.txt").write_text("This is the content of file 2.")
    (test_dir / "IgnorePath" / "file3.txt").write_text("This file should be ignored.")

    # Also include a python file to test extractor selection
    (test_dir / "script.py").write_text("import os\nprint('Hello, world!')")

    # Also include a PDF file to test extractor selection
    pdf_writer = pypdf.PdfWriter()
    pdf_writer.add_blank_page(width=72, height=72)
    pdf_writer.add_blank_page(width=72, height=72)
    with open(test_dir / "document.pdf", "wb") as f:
        pdf_writer.write(f)

    all_documents = list(test_dir.rglob("*"))
    all_documents = [p for p in all_documents if p.is_file()]

    all_ignored_files = list((test_dir / "IgnorePath").rglob("*"))
    return test_dir, all_documents, all_ignored_files

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

    attatchment_types = ["text/plain", "application/pdf", "image/png"]
    from .attatchments import attachment_content_bytes

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
        
        if i==1:
            # Add attachments to the first message
            for att_type in attatchment_types:
                msg.add_attachment(attachment_content_bytes[att_type], maintype=att_type.split("/")[0], subtype=att_type.split("/")[1], filename=f"attachment_{att_type.replace('/', '_')}")


        mbox.add(msg)


    mbox.flush()
    mbox.close()


    return str(mbox_path)

@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture
def setup_test_filesystem(tmp_path) -> Path:
    """
    Fixture to set up a test filesystem with some files and directories.
    """
    base_dir = tmp_path / "data_fs"
    base_dir.mkdir()

    # Create some files and directories
    f1 = (base_dir / "a.txt").write_text("hello world")
    f2 = (base_dir / "b.txt").write_text("second file")
    f3 = (base_dir / "c.txt").write_text("third file")
    
    # Also create one PDF file to test extractor selection
    import pypdf
    from io import BytesIO
    pdf_writer = pypdf.PdfWriter()
    pdf_writer.add_blank_page(width=72, height=72)
    pdf_bytes = BytesIO()
    pdf_writer.write(pdf_bytes)
    (base_dir / "d.pdf").write_bytes(pdf_bytes.getvalue())

    
    return base_dir
