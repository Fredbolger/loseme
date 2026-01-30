from api.app.tasks.celery_app import celery_app
from src.core.wiring import build_chunker, build_embedding_provider
from storage.metadata_db.document import upsert_document
from storage.metadata_db.processed_documents import mark_processed, is_processed
from storage.metadata_db.indexing_runs import update_status, is_stop_requested
from storage.vector_db.runtime import get_vector_store
from src.domain.ids import make_chunk_id
from src.domain.models import Chunk, Document
import logging

logger = logging.getLogger(__name__)

store = get_vector_store()
chunker = build_chunker()
embedding_provider = build_embedding_provider()

@celery_app.task(bind=True)
def ingest_run_task(self, run_id: str, documents: list[dict]):
    update_status(run_id = run_id, status='running')

    try:
        for doc in documents:
            if is_processed(source_instance_id = doc["source_id"],
                            content_checksum = doc["checksum"]):
                logger.info(f"Skipping already processed document ID: {doc['id']}")
                continue

            if is_stop_requested(run_id = run_id):
                update_status(run_id = run_id, status='interrupted')
                return

            ingest_single_document(doc)
            mark_processed(run_id = run_id,
                             source_instance_id = doc["source_id"],
                             content_checksum = doc["checksum"],
                             )
        update_status(run_id = run_id, status='completed')

    except Exception as e:
        update_status(run_id = run_id, status='failed')
        raise

def ingest_single_document(doc: dict):
    if not doc.get("text"):
        raise ValueError("Document must contain 'text' field for ingestion.")
    logger.info(f"Starting ingestion for document ID: {doc['id']} with size {len(doc['text'])} characters")

    document = Document(
            id=doc["id"],
            source_type=doc["source_type"],
            source_id=doc["source_id"],
            device_id=doc["device_id"],
            source_path=doc["source_path"],
            text=doc["text"],
            checksum=doc["checksum"],
            metadata=doc.get("metadata", {}),
            created_at=doc.get("created_at"),
            updated_at=doc.get("updated_at"),
            )

    chunks, chunk_text = chunker.chunk(document, doc["text"])

    for c in chunks:
        chunk_id = make_chunk_id(
                document_id=doc["id"],
                document_checksum=doc["checksum"],
                index=c.index,
            )
        chunk = Chunk(
                id=chunk_id,
                source_type=doc["source_type"],
                text=chunk_text[c.index],
                document_id=doc["id"],
                document_checksum=doc["checksum"],
                device_id=doc["device_id"],
                source_path=doc["source_path"],
                index=c.index,
                metadata=c.metadata,
                )

        embedding = embedding_provider.embed_query(chunk.text)
        # Store in Qdrant
        store.add(chunk, embedding)

    upsert_document({
        "id": doc["id"],
        "source_type": doc["source_type"],
        "source_id": doc["source_id"],
        "device_id": doc["device_id"],
        "source_path": doc["source_path"],
        "checksum": doc["checksum"],
        "metadata": doc.get("metadata", {}),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    })

