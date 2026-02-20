from pathlib import Path
from importlib.util import spec_from_file_location, module_from_spec
import sqlite3

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

def ensure_migration_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY
        );
        """
    )

def applied_migrations(conn: sqlite3.Connection) -> set[str]:
    cur = conn.execute("SELECT version FROM schema_migrations;")
    return {row[0] for row in cur.fetchall()}

def run_migrations(conn: sqlite3.Connection) -> None:
    ensure_migration_table(conn)
    done = applied_migrations(conn)

    for path in sorted(MIGRATIONS_DIR.iterdir()):
        if path.suffix not in {".sql", ".py"}:
            continue

        version = path.stem
        if version in done:
            continue

        if path.suffix == ".sql":
            conn.executescript(path.read_text())

        elif path.suffix == ".py":
            spec = spec_from_file_location(version, path)
            module = module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(module)

            if not hasattr(module, "run"):
                raise RuntimeError(f"{path.name} has no run(conn)")

            module.run(conn)

        conn.execute(
            "INSERT INTO schema_migrations (version) VALUES (?);",
            (version,),
        )
