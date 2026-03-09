import pytest

@pytest.fixture
def setup_db(tmp_path, monkeypatch):
    test_db_path = tmp_path / "test_metadata.db"

    # Patch the path FIRST, before anything touches the database
    monkeypatch.setattr("storage.metadata_db.db.DB_PATH", test_db_path)

    # Also reset the vector store singleton so it doesn't hold
    # a connection opened against a previous DB_PATH
    import storage.vector_db.runtime as rt
    monkeypatch.setattr(rt, "_vector_store", None)

    # Now it's safe to initialise — writes to the temp file
    from storage.metadata_db.db import init_db
    init_db()

    yield test_db_path

@pytest.fixture(autouse=True)
def reset_vector_store_singleton():
    """
    runtime.py caches the store in a module-level global.
    Reset it before every test so monkeypatch substitutions take effect.
    """
    import storage.vector_db.runtime as rt
    rt._vector_store = None
    yield
    rt._vector_store = None
