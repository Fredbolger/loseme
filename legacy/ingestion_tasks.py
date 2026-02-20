from api.app.tasks.celery_app import celery_app
from src.core.wiring import build_chunker, build_embedding_provider
#from storage.metadata_db.document_parts import upsert_document_part
from storage.metadata_db.processed_document_parts import mark_part_processed, part_is_processed, add_discovered_document_part, get_all_parts
from storage.metadata_db.indexing_runs import update_status, is_stop_requested, increment_indexed_count, increment_discovered_count
from storage.vector_db.runtime import get_vector_store
from src.core.ids import make_chunk_id
from src.sources.base.models import Chunk, Document, DocumentPart
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

store = get_vector_store()
chunker = build_chunker()
embedding_provider = build_embedding_provider()

@celery_app.task(bind=True)
def ingest_run_task(self, run_id: str, documents: list[dict], update_if_changed_after: datetime = None):

    try:
        for doc in documents:
            skip_part = False
            
            for part in doc["parts"]:
                is_processed, extractor_dict = part_is_processed(source_instance_id = doc["source_id"],
                                                                unit_locator=part["unit_locator"],
                                                                )
                if is_processed:
                    skip_part = True
                    logger.info(f"Document part with source_instance_id: {doc['source_id']} and unit_locator: {part['unit_locator']} is already processed. Suggest skipping ingestion of this part.")
                
                    logger.debug(f"Part was extracted with extractor: {extractor_dict.get('extractor_name')} version {extractor_dict.get('extractor_version')}")

                    logger.debug(f"Current extractor for this part is: {part['extractor_name']} version {part['extractor_version']}")

                    # However, even if a document part was already processed, we still want to check for an change in the extractor_registry
                    if part["extractor_name"] != extractor_dict.get("extractor_name") or part["extractor_version"] != extractor_dict.get("extractor_version"):
                        logger.info(f"Extractor for document part with source_instance_id: {doc['source_id']} and unit_locator: {part['unit_locator']} has changed since last processing. Suggest re-processing this part.")
                        skip_part = False


            if skip_part:
                logger.info(f"Skipping ingestion for document ID: {doc['id']} since all parts are already processed and no extractor changes detected.")
                increment_indexed_count(run_id = run_id, count = 1)
                continue

            if is_stop_requested(run_id = run_id):
                update_status(run_id = run_id, status='interrupted')
                return
    
            result = ingest_single_document(doc)

            if result:
                for part_id, part in enumerate(doc["parts"]):
                    mark_part_processed(run_id = run_id,
                                     source_instance_id = doc["source_id"],
                                     chunk_ids = result[part_id],
                                     content_checksum = doc["checksum"],
                                     unit_locator=part["unit_locator"],
                                     content_type=part["content_type"],
                                     extractor_name=part["extractor_name"],
                                     extractor_version=part["extractor_version"]
                                     )
                increment_indexed_count(run_id = run_id, count = 1)
            else:
                logger.warning(f"Ingestion failed for document ID: {doc['id']}. Document was not marked as processed.")
                continue

    except Exception as e:
        raise

def ingest_single_part(part: dict, document: dict, run_id: str = None) -> bool:
        is_processed, extractor_dict = part_is_processed(source_instance_id = part["source_id"],
                                                        unit_locator=part["unit_locator"],
                                                        )
        skip_part = False

        if is_processed:
            skip_part = True
            # However, even if a document part was already processed, we still want to check for an change in the extractor_registry
            if part["extractor_name"] != extractor_dict.get("extractor_name") or part["extractor_version"] != extractor_dict.get("extractor_version"):
                logger.info(f"Extractor for document part with source_instance_id: {part['source_id']} and unit_locator: {part['unit_locator']} has changed since last processing. Suggest re-processing this part.")
                skip_part = False

        if skip_part == False:
            chunk_ids = []
            chunks, chunk_texts = chunker.chunk_single_part(document, part)
            for chunk, chunk_text in zip(chunks, chunk_texts):
                # Skip if there is no text to embed
                if not chunk_text:
                    embedding = embedding_provider.embed_query("")
                else:
                    embedding = embedding_provider.embed_query(chunk_text)
                # If there is an old chunk for this same part (source_instance_id, unit_locator) -> delete
                
                old_parts = get_all_parts(source_instance_id = part["source_id"])
                for old_part in old_parts:
                    if old_part["unit_locator"] == part["unit_locator"]:
                        old_chunk_ids = old_part["chunk_ids"]
                        for old_chunk_id in old_chunk_ids:
                            store.delete(old_chunk_id)
                

                # Store in Qdrant
                chunk_id = store.add(chunk, embedding)
                chunk_ids.append(chunk_id)

            mark_part_processed(run_id = run_id,
                                source_instance_id = part["source_id"],
                                chunk_ids = chunk_ids,
                                content_checksum = part["content_checksum"],
                                unit_locator=part["unit_locator"],
                                content_type=part["content_type"],
                                extractor_name=part["extractor_name"],
                                extractor_version=part["extractor_version"]
                                )

   
def ingest_single_document(doc: dict, run_id: str = None) -> bool:
    document = Document.deserialize(doc)
 
    # Add the document to the metadata database (or update if it already exists)
    upsert_document_part({
        "document_part_id": doc["document_part_id"],
        "checksum": doc["checksum"],
        "source_type": doc["source_type"],
        "source_instance_id": doc["source_instance_id"],
        "device_id": doc["device_id"],
        "source_path": doc["source_path"],
        "metadata_json": doc.get("metadata", {}),
        "unit_locator": doc["unit_locator"],
        "content_type": doc.get("content_type"),
        "extractor_name": doc.get("extractor_name"),
        "extractor_version": doc.get("extractor_version"),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }, run_id=run_id)
    # Only increment the discovered count after upserting the document
    increment_discovered_count(run_id = run_id, count = 1)

    # Add all discovered parts to the metadata database
    for part in document.parts:
        add_discovered_document_part(
            run_id = run_id,
            source_instance_id = document.source_id,
            content_checksum = document.checksum,
            unit_locator = part.unit_locator,
            content_type = part.content_type,
            extractor_name = part.extractor_name,
            extractor_version = part.extractor_version
        )

    chunked_parts = chunker.chunk(document)
    # For each part of the document, there can be multiple chunks
    """
    Document
        |- Part 1
        |   |- Chunk 1
        |   |- Chunk 2
        |- Part 2
            |- Chunk 1
            |- Chunk 2
    """
    # Chunked parts is a List of tuples: (List[Chunk], part_text)

    chunk_ids = []
    for part in chunked_parts:
        chunk_ids_for_part = []
        chunks, chunk_text = part
        for c in chunks:
            # Skip if there is no text to embed
            if not c.text:
                embedding = embedding_provider.embed_query("")
            else:
                embedding = embedding_provider.embed_query(c.text)
            # Store in Qdrant
            chunk_id = store.add(c, embedding)
            chunk_ids_for_part.append(chunk_id)
        chunk_ids.append(chunk_ids_for_part)
    

    return chunk_ids
