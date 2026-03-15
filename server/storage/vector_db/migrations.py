from pathlib import Path
import sqlite3
from importlib.util import spec_from_file_location, module_from_spec
import logging

logger = logging.getLogger(__name__)

VECTOR_MIGRATIONS_DIR = Path(__file__).parent / "migrations"

def ensure_vector_migration_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS vector_migrations (
            version TEXT PRIMARY KEY
        );
        """
    )

def applied_vector_migrations(conn):
    cur = conn.execute("SELECT version FROM vector_migrations;")
    return {row[0] for row in cur.fetchall()}

def run_vector_migrations(conn, qdrant_client, collection_name: str):
    ensure_vector_migration_table(conn)
    done = applied_vector_migrations(conn)

    for path in sorted(VECTOR_MIGRATIONS_DIR.iterdir()):
        if path.suffix != ".py":
            continue

        version = path.stem
        if version in done:
            continue

        spec = spec_from_file_location(version, path)
        module = module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)

        if not hasattr(module, "run"):
            raise RuntimeError(f"{path.name} has no run(...)")

        with conn:
            logger.info(f"Running vector migration: {version}")
            module.run(conn, qdrant_client, collection_name)
            logger.info(f"Finished vector migration: {version}")

            conn.execute(
               "INSERT INTO vector_migrations (version) VALUES (?);",
                (version,),
                )
            
