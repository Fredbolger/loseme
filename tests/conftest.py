import pytest
from storage.metadata_db.db import init_db
from storage.vector_db.runtime import get_vector_store
from storage.metadata_db.db import delete_database

def clear_all():
    vector_store = get_vector_store()
    vector_store.delete_collection()
    delete_database()


@pytest.fixture
def setup_db():
    """
    Initialize a fresh database for testing.
    """
    init_db()
    yield
    clear_all()

@pytest.fixture
def set_embedding_model_env(monkeypatch):
    monkeypatch.setenv("EMBEDDING_MODEL", "bge-m3")
    return "EMBEDDING_MODEL"
