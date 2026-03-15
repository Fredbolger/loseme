import logging

logger = logging.getLogger(__name__)

def run(conn, qdrant_client, collection_name: str):
    from qdrant_client import models

    logger.info("Starting Thunderbird source_path backfill migration...")

    BATCH_SIZE = 500

    scroll_filter = models.Filter(
        must=[
            models.FieldCondition(
                key="source_type",
                match=models.MatchValue(value="thunderbird"),
            ),
            models.IsEmptyCondition(
                is_empty=models.PayloadField(key="source_path")
            ),
        ],
    )

    offset = None
    total_updated = 0

    while True:
        points, offset = qdrant_client.scroll(
            collection_name=collection_name,
            scroll_filter=scroll_filter,
            with_payload=True,
            limit=BATCH_SIZE,
            offset=offset,
        )

        if not points:
            break

        document_ids = [
            (p.payload or {}).get("document_part_id")
            for p in points
            if (p.payload or {}).get("document_part_id")
        ]

        if document_ids:
            placeholders = ",".join("?" * len(document_ids))
            rows = conn.execute(
                    f"SELECT document_part_id, source_path FROM document_parts WHERE document_part_id IN ({placeholders})",
                document_ids,
            ).fetchall()
            source_path_map = {row[0]: row[1] for row in rows}
        else:
            source_path_map = {}

        update_operations = []
        for point in points:
            document_id = (point.payload or {}).get("document_part_id")
            source_path = source_path_map.get(document_id) if document_id else None
            if not source_path:
                continue
            update_operations.append(
                models.SetPayloadOperation(
                    set_payload=models.SetPayload(
                        payload={"source_path": source_path},
                        points=[point.id],
                    )
                )
            )

        if update_operations:
            qdrant_client.batch_update_points(
                collection_name=collection_name,
                update_operations=update_operations,
            )
            total_updated += len(update_operations)
            logger.info(f"Updated {total_updated} points so far...")

        if offset is None:
            break

    logger.info(f"Migration complete. Total points updated: {total_updated}")
