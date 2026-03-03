import logging
from storage.metadata_db.monitor_sources import list_all_monitored_sources
from src.sources.thunderbird.thunderbird_source import ThunderbirdIngestionSource
from src.sources.thunderbird.thunderbird_model import ThunderbirdIndexingScope
from storage.vector_db.qdrant_store_hybrid import chunk_id_to_uuid

logger = logging.getLogger(__name__)

batch_size = 100

def run(conn, qdrant_client, collection_name: str):
    from qdrant_client import models
    from storage.metadata_db.document_parts import get_document_part_by_id
    import json

    logger.info("Starting backfill of Thunderbird message index")

    # Get all monitored sources
    sources = list_all_monitored_sources()
    for source in sources:
        logger.debug(f"Checking source: {source}")
        print(f"Checking source: {source}")
        if source["source_type"] == "thunderbird":
            logger.info(f"Backfilling index for Thunderbird source with ID {source['id']} and locator {source['locator']}")
           
            scope = source["scope"]

            print(f"Backfilling index for Thunderbird scope: {scope}")

            # Create an instance of the ingestion scope
            indexing_scope = ThunderbirdIndexingScope.deserialize(scope.model_dump())
           
            # Create the ThunderbirdIngestionSource instance
            ingestion_source = ThunderbirdIngestionSource(scope=indexing_scope, should_stop=lambda: False)
            
            batch_updates = []
            
            dry_run = False
            
            for message in ingestion_source.iter_documents():
                index = message.metadata.get("index", 0)
                if dry_run:
                    # Terminate after first message and print the entire update operation for inspection
                    if index >= 1:
                        print("Dry run complete - stopping after 1 message")
                        
                        print("Example batch update operation:")
                        for update in batch_updates:
                            print(update)
                        
                        # Try a sinle update operation to see if it works as expected
                        if batch_updates:
                            print("Testing a single update operation with Qdrant client")
                            qdrant_client.batch_update_points(
                                collection_name=collection_name,
                                update_operations=batch_updates[:1],  # just test the first one
                            )
                            

                        break
                    
                for part in message.parts:
                    document_part_id = part.document_part_id if part.document_part_id else None
                    document_part = get_document_part_by_id(document_part_id)

                    chunk_ids = document_part.get("chunk_ids", [])
                    # Turn chunk ids back to a directory after the row of the db is returned
                    chunk_ids = json.loads(chunk_ids) if chunk_ids else []
                    
                    if not chunk_ids:
                        print(f"No chunk ids found for document part {document_part_id}, skipping")
                        continue

                    for chunk_id in chunk_ids:
                        point_id = chunk_id_to_uuid(chunk_id)
                        batch_updates.append(
                            models.SetPayloadOperation(
                                set_payload=models.SetPayload(
                                    payload={"index": index},
                                    points=[point_id],
                                )
                            )
                        )

                        # Send batch if it's full
                        if len(batch_updates) >= batch_size:
                            print(f"Updating batch of {len(batch_updates)} payloads")
                            if dry_run:
                                print(f"Dry run mode - not sending updates to Qdrant")
                            else:
                                qdrant_client.batch_update_points(
                                    collection_name=collection_name,
                                    update_operations=batch_updates,
                                )
                                batch_updates = []  # Reset batch

            # Don't forget to send any remaining updates
            if batch_updates:
                if dry_run:
                    print(f"Dry run mode - not sending final batch of {len(batch_updates)} payloads to Qdrant")
                else:
                    print(f"Updating final batch of {len(batch_updates)} payloads")
                    qdrant_client.batch_update_points(
                        collection_name=collection_name,
                        update_operations=batch_updates,
                    )            

    print("Finished backfilling Thunderbird message index")
