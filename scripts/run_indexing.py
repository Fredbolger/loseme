import signal
from pathlib import Path
import hashlib
from src.core.logging import logger
from src.domain.models import IndexingScope
from collectors.filesystem.filesystem_source import FilesystemIngestionSource
from pipeline.chunking.simple_chunker import SimpleTextChunker
from pipeline.embeddings.dummy import DummyEmbeddingProvider
from storage.metadata_db.db import init_db, log_active_schema
from storage.metadata_db.indexing_runs import (
    create_run,
    load_latest_run,
    update_checkpoint,
    update_status,
)
from storage.metadata_db.processed_documents import (
    mark_processed,
    is_processed,
    get_all_processed,
)


def compute_doc_hash(content: str) -> str:
    """Compute a SHA256 hash for a document."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def run_indexing():
    logger.info("=== Starting indexing process ===")

    init_db()
    log_active_schema()
    logger.debug("Metadata DB initialized")

    scope = IndexingScope(directories=[Path("./docs")])
    logger.info(f"Indexing scope: {scope.directories}")

    source = FilesystemIngestionSource(scope)

    resume_run = load_latest_run("filesystem", scope)

    if resume_run is None:
        run = create_run("filesystem", scope)
        logger.info("Created new indexing run %s", run.id)
    else:
        run = resume_run
        logger.info(
            "Resuming indexing run %s (status=%s)",
            run.id,
            run.status,
        )

    # --- Interrupt handler -------------------------------------------------
    def handle_interrupt(signum, frame):
        logger.warning(
            f"SIGINT received → marking run {run.id} as interrupted"
        )
        update_status(run.id, "interrupted")
        logger.info("Run marked as interrupted, exiting")
        exit(0)

    signal.signal(signal.SIGINT, handle_interrupt)

    # --- Indexing loop -----------------------------------------------------
    logger.info(
        f"Listing documents (after checkpoint={run.last_document_id})"
    )
    documents = source.list_documents(after=run.last_document_id)
    logger.info(f"{len(documents)} documents discovered")

    for doc in documents:
        doc_id = str(doc.path)
        logger.debug(f"Considering document: {doc_id}")
    
        doc_hash = doc.checksum

        if is_processed(run.id, doc_id, doc_hash):
            logger.info(f"Skipping already processed and unchanged document: {doc_id}")
            continue

        logger.info(f"Processing document: {doc_id}")

        chunker = SimpleTextChunker()
        chunks = chunker.chunk(doc, doc.content)
        logger.debug(f"Produced {len(chunks)} chunks")

        embedding_provider = DummyEmbeddingProvider()
        for i, chunk in enumerate(chunks):
            embedding = embedding_provider.embed(chunk.content)
            logger.debug(
                f"Embedded chunk {i + 1}/{len(chunks)} "
                f"(len={len(chunk.content)})"
            )
            # vector DB insert will go here

        mark_processed(run.id, doc_id, doc_hash)
        update_checkpoint(run.id, doc_id)

        logger.info(f"Indexed document {doc_id}, {len(chunks)} chunks")

    update_status(run.id, "completed")
    logger.info(f"Indexing run {run.id} completed successfully")


if __name__ == "__main__":
    run_indexing()

