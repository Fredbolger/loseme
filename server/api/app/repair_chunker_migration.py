"""
repair_chunker_migration.py
───────────────────────────
Lightweight repair for document_parts rows where the upsert was skipped
during a re-indexing run with a new chunker.

The vectors are already correct in Qdrant. This script only:
  1. Finds all document_parts rows where chunker_name/version don't match
     the currently configured chunker.
  2. Scrolls Qdrant to collect the current chunk_ids for each part
     (via the document_part_id payload field).
  3. Removes any stale chunk_ids recorded in the SQLite row from Qdrant
     (left over from before the broken run).
  4. Updates the SQLite row: chunker_name, chunker_version, chunk_ids,
     last_indexed_at, updated_at.

Usage
─────
  python repair_chunker_migration.py --dry-run   # inspect only
  python repair_chunker_migration.py --limit 10  # smoke-test
  python repair_chunker_migration.py             # full repair
  python repair_chunker_migration.py --part-id <id>
"""

import argparse
import json
import logging
import sys
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("repair")

COLLECTION = "chunks"
SCROLL_BATCH = 100


def _now() -> str:
    return datetime.utcnow().isoformat()


def _load_chunk_ids(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        return json.loads(raw)
    except Exception:
        return []


def _fetch_chunk_ids_from_qdrant(qdrant_client, document_part_id: str) -> list[str]:
    """Return all chunk_id payload values for a given document_part_id."""
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    chunk_ids = []
    offset = None

    while True:
        results, next_offset = qdrant_client.scroll(
            collection_name=COLLECTION,
            scroll_filter=Filter(
                must=[FieldCondition(
                    key="document_part_id",
                    match=MatchValue(value=document_part_id),
                )]
            ),
            limit=SCROLL_BATCH,
            offset=offset,
            with_payload=["chunk_id"],
            with_vectors=False,
        )
        for point in results:
            if cid := point.payload.get("chunk_id"):
                chunk_ids.append(cid)
        if next_offset is None:
            break
        offset = next_offset

    return chunk_ids


def repair(
    *,
    dry_run: bool = False,
    target_part_id: str | None = None,
    limit: int | None = None,
) -> None:
    from storage.metadata_db.db import fetch_all, execute
    from storage.vector_db.runtime import get_vector_store
    from wiring import build_chunker

    chunker = build_chunker()
    store = get_vector_store()
    qdrant_client = store.client

    logger.info("Current chunker: name=%r  version=%r", chunker.name, chunker.version)

    if target_part_id:
        rows = fetch_all(
            "SELECT document_part_id, chunker_name, chunker_version, chunk_ids "
            "FROM document_parts WHERE document_part_id = ?",
            (target_part_id,),
        )
    else:
        rows = fetch_all(
            """
            SELECT document_part_id, chunker_name, chunker_version, chunk_ids
            FROM document_parts
            WHERE chunker_name != ?
               OR chunker_version != ?
               OR chunk_ids IS NULL
            """,
            (chunker.name, chunker.version),
        )

    rows = [dict(r) for r in rows]
    if limit:
        rows = rows[:limit]

    total = len(rows)
    logger.info("Found %d document_part(s) to repair.", total)
    if total == 0:
        logger.info("Nothing to do.")
        return

    repaired = 0
    skipped = 0
    errors = 0

    for i, row in enumerate(rows, 1):
        part_id = row["document_part_id"]
        old_chunker = row.get("chunker_name") or "<null>"
        old_version = row.get("chunker_version") or "<null>"
        stale_chunk_ids = _load_chunk_ids(row.get("chunk_ids"))

        logger.info(
            "[%d/%d] %s  (%s@%s → %s@%s, stale_ids: %d)",
            i, total, part_id,
            old_chunker, old_version,
            chunker.name, chunker.version,
            len(stale_chunk_ids),
        )

        try:
            # 1. Collect current chunk_ids from Qdrant for this part.
            current_chunk_ids = _fetch_chunk_ids_from_qdrant(qdrant_client, part_id)
            logger.info("  ↳ Qdrant has %d current chunk(s).", len(current_chunk_ids))

            if not current_chunk_ids:
                logger.warning("  ↳ No chunks found in Qdrant — skipping.")
                skipped += 1
                continue

            # 2. Remove stale chunk_ids (the ones recorded in SQLite before
            #    the broken run) that are no longer in Qdrant's current set.
            truly_stale = [cid for cid in stale_chunk_ids if cid not in set(current_chunk_ids)]
            if truly_stale:
                logger.info("  ↳ Removing %d truly stale vector(s) from Qdrant.", len(truly_stale))
                if not dry_run:
                    store.remove_chunks(chunk_ids=truly_stale)
            else:
                logger.info("  ↳ No stale vectors to remove.")

            if dry_run:
                logger.info(
                    "  ↳ [DRY-RUN] Would update SQLite: chunker=%s@%s, chunk_ids=%d.",
                    chunker.name, chunker.version, len(current_chunk_ids),
                )
                continue

            # 3. Update the SQLite row.
            now = _now()
            execute(
                """
                UPDATE document_parts
                SET chunker_name    = ?,
                    chunker_version = ?,
                    chunk_ids       = ?,
                    last_indexed_at = ?,
                    updated_at      = ?
                WHERE document_part_id = ?
                """,
                (
                    chunker.name,
                    chunker.version,
                    json.dumps(current_chunk_ids),
                    now,
                    now,
                    part_id,
                ),
            )
            logger.info(
                "  ↳ Updated: chunker=%s@%s, %d chunk_id(s).",
                chunker.name, chunker.version, len(current_chunk_ids),
            )
            repaired += 1

        except Exception as exc:
            logger.error("  ↳ ERROR: %s", exc, exc_info=True)
            errors += 1

    logger.info(
        "\nDone.  repaired=%d  skipped=%d  errors=%d  (dry_run=%s)",
        repaired, skipped, errors, dry_run,
    )
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--part-id", metavar="ID")
    parser.add_argument("--limit", type=int, metavar="N")
    args = parser.parse_args()

    repair(
        dry_run=args.dry_run,
        target_part_id=args.part_id,
        limit=args.limit,
    )
