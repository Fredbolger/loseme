import os
from pathlib import Path

from src.domain.models import IndexingScope
from api.app.services.ingestion import ingest_filesystem_scope
from storage.metadata_db.db import init_db


def main():
    # REQUIRED invariant
    device_id = os.environ.get("LOSEME_DEVICE_ID")
    if not device_id:
        raise RuntimeError("LOSEME_DEVICE_ID must be set")

    init_db()

    scope = IndexingScope(
        directories=[Path(os.environ.get("LOSEME_INDEX_PATH", "."))],
        recursive=True,
    )

    result = ingest_filesystem_scope(scope)

    print(
        f"Ingestion finished: "
        f"discovered={result.documents_discovered}, "
        f"indexed={result.documents_indexed}"
    )


if __name__ == "__main__":
    main()

