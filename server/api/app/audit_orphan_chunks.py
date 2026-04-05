"""
audit_orphan_chunks.py
──────────────────────
Scans every point in the Qdrant `chunks` collection and checks whether its
`document_part_id` payload field references a document_part row in SQLite.

Points with no matching SQLite row are "orphans" — they waste vector storage
and will never be returned in a meaningful search result.

What this script does:
  1. Loads all document_part_ids from SQLite into a set.
  2. Scrolls the entire Qdrant collection in batches.
  3. Collects any point whose document_part_id is missing from SQLite.
  4. Reports the orphans (and optionally deletes them with --delete).

Usage
─────
  # Audit only — print orphan count and a sample:
  python audit_orphan_chunks.py

  # Delete the orphaned points from Qdrant:
  python audit_orphan_chunks.py --delete

  # Delete but only after a dry-run confirmation:
  python audit_orphan_chunks.py --delete --dry-run
"""

import argparse
import json
import logging
import sys
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("audit")

COLLECTION = "chunks"
SCROLL_BATCH = 500


def audit(*, delete: bool = False, dry_run: bool = False) -> None:
    from storage.metadata_db.db import fetch_all
    from storage.vector_db.runtime import get_vector_store
    from qdrant_client.models import PointIdsList

    store = get_vector_store()
    qdrant_client = store.client

    # ── 1. Load all known document_part_ids from SQLite ───────────────────────
    rows = fetch_all("SELECT document_part_id FROM document_parts")
    known_part_ids = {row["document_part_id"] for row in rows}
    logger.info("SQLite has %d document_part_id(s).", len(known_part_ids))

    # ── 2. Scroll all Qdrant points ───────────────────────────────────────────
    total_points = 0
    orphan_point_ids = []          # Qdrant UUIDs to delete
    orphans_by_part: defaultdict   = defaultdict(list)  # for reporting

    offset = None
    batch = 0

    while True:
        results, next_offset = qdrant_client.scroll(
            collection_name=COLLECTION,
            limit=SCROLL_BATCH,
            offset=offset,
            with_payload=["document_part_id", "chunk_id"],
            with_vectors=False,
        )

        batch += 1
        total_points += len(results)

        for point in results:
            part_id = point.payload.get("document_part_id")
            chunk_id = point.payload.get("chunk_id", "<unknown>")

            if part_id not in known_part_ids:
                orphan_point_ids.append(point.id)
                orphans_by_part[part_id].append(chunk_id)

        if batch % 10 == 0:
            logger.info(
                "  Scanned %d points so far, %d orphan(s) found...",
                total_points, len(orphan_point_ids),
            )

        if next_offset is None:
            break
        offset = next_offset

    # ── 3. Report ─────────────────────────────────────────────────────────────
    logger.info(
        "\nScan complete. total_points=%d  orphaned_points=%d  orphaned_parts=%d",
        total_points, len(orphan_point_ids), len(orphans_by_part),
    )

    if not orphan_point_ids:
        logger.info("✓ No orphans found — Qdrant and SQLite are in sync.")
        return

    # Print a sample so the caller can sanity-check before deleting.
    sample = list(orphans_by_part.items())[:10]
    logger.info("\nOrphaned document_part_ids (up to 10 shown):")
    for part_id, chunk_ids in sample:
        logger.info("  part_id=%s  chunks=%d", part_id, len(chunk_ids))

    if not delete:
        logger.info(
            "\nRun with --delete to remove these %d orphaned point(s) from Qdrant.",
            len(orphan_point_ids),
        )
        return

    # ── 4. Delete orphans ─────────────────────────────────────────────────────
    if dry_run:
        logger.info(
            "[DRY-RUN] Would delete %d orphaned point(s) from Qdrant.",
            len(orphan_point_ids),
        )
        return

    BATCH_SIZE = 500
    deleted = 0
    for start in range(0, len(orphan_point_ids), BATCH_SIZE):
        batch_ids = orphan_point_ids[start : start + BATCH_SIZE]
        qdrant_client.delete(
            collection_name=COLLECTION,
            points_selector=PointIdsList(points=batch_ids),
        )
        deleted += len(batch_ids)
        logger.info("  Deleted %d / %d orphaned point(s).", deleted, len(orphan_point_ids))

    logger.info("Done. Removed %d orphaned point(s) from Qdrant.", deleted)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Audit (and optionally delete) Qdrant chunks with no matching document_part."
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete orphaned points from Qdrant after the audit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="With --delete: print what would be deleted without actually deleting.",
    )
    args = parser.parse_args()

    audit(delete=args.delete, dry_run=args.dry_run)
