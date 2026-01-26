import warnings
import os
from src.domain.models import FilesystemIndexingScope,  ThunderbirdIndexingScope, IndexingScope, IngestionSource
from collectors.filesystem.filesystem_source import FilesystemIngestionSource
from collectors.thunderbird.thunderbird_source import ThunderbirdIngestionSource
from storage.metadata_db.indexing_runs import create_run, load_latest_run_by_scope, is_stop_requested, load_latest_interrupted, set_run_resume, load_run_by_id
from storage.metadata_db.processed_documents import is_processed, mark_processed
from storage.metadata_db.db import init_db
from src.core.wiring import build_extractor_registry, build_chunker, build_embedding_provider
from dataclasses import dataclass
from storage.vector_db.runtime import get_vector_store
from storage.metadata_db.document import upsert_document
from storage.metadata_db.indexing_runs import update_status
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

extractor_registry = build_extractor_registry()
chunker = build_chunker()
embedding_provider = build_embedding_provider()
base_path = os.getenv("LOSEME_SOURCE_ROOT_HOST")
if base_path is None:
    raise RuntimeError("LOSEME_SOURCE_ROOT_HOST environment variable is not set")


@dataclass
class IngestionResult:
    run_id: str
    status: str = "completed"
    documents_discovered: int = 0
    documents_indexed: int = 0

class IngestionCancelled(Exception):
    pass

def ingest_scope(scope: IndexingScope, run_id: str, resume: bool = False, stop_after: int | None = None) -> IngestionResult:
    if stop_after is not None:
        warnings.warn("The 'stop_after' parameter is set, which will intentionally limit the number of documents processed. This is for testing purposes only and should not be used in production.", UserWarning)

    init_db()
    
    run = None

    if resume:
        run = load_latest_interrupted(scope.type)
        if run:
            run_id = run.id
            logger.info(f"Resuming {scope.type} ingestion from interrupted run {run_id} for scope: {scope}")
            if scope.type == "filesystem":
                # log the direcories
                for dir in scope.directories:
                    logger.info(f"Resuming ingestion from directory: {str(dir)}")
            set_run_resume(run_id)
        else:
            logger.info(f"No interrupted {scope.type} ingestion run found for scope: {scope}.")
            raise RuntimeError("resume=True but no interrupted run to resume from.")

    if run_id is None:
        raise ValueError("run_id must be provided when resume is False")
   
    if run is None:
        run = load_run_by_id(run_id)

    logger.info(f"Starting {scope.type} ingestion for scope: {scope} with run_id: {run_id}, resume={resume}")
    
    def stop_requested() -> bool:
        return is_stop_requested(run_id)

    source = IngestionSource.from_scope(scope, stop_requested)
    vector_store = get_vector_store()
    
    if embedding_provider.dimension() != vector_store.dimension():
        raise RuntimeError("Embedding dimension mismatch with vector store")

    documents_discovered = run.discovered_document_count
    documents_indexed = run.indexed_document_count
    
    update_status(run_id, "running")

    try:
        for doc in source.iter_documents():
            if stop_after is not None and documents_indexed >= stop_after:
                raise IngestionCancelled("Ingestion stopped after reaching the stop_after limit.")    
            documents_discovered += 1
            logger.debug(f"Discovered document with ID {doc.id}")

            if is_processed(doc.source_id, doc.checksum):
                logger.info(f"Document with ID {doc.id} already processed with same checksum, skipping.")
                continue
             
            upsert_document(doc)
            
            chunks, chunk_texts = chunker.chunk(doc, doc.text)
            embeddings = [embedding_provider.embed_query(text) for text in chunk_texts]
            for chunk, embedding in zip(chunks, embeddings):
                vector_store.add(chunk, embedding)

            mark_processed(run_id, doc.source_id, doc.checksum)
            documents_indexed += 1

        if stop_requested():
            update_status(run_id, "interrupted")
            logger.info(f"{scope.type} ingestion run {run_id} stopped. Discovered {documents_discovered} documents, indexed {documents_indexed} documents.")
            return IngestionResult(
                run_id=run_id,
                status="interrupted",
                documents_discovered=documents_discovered,
                documents_indexed=documents_indexed
            )

        else:
            update_status(run_id, "completed")
            logger.info(f"{scope.type} ingestion run {run_id} completed successfully. Discovered {documents_discovered} documents, indexed {documents_indexed} documents.")
        
            return IngestionResult(
                run_id=run_id,
                status="completed",
                documents_discovered=documents_discovered,
                documents_indexed=documents_indexed
            )

    except IngestionCancelled:
        update_status(run_id, "interrupted")
        return IngestionResult(
            run_id=run_id,
            status="interrupted",
            documents_discovered=documents_discovered,
            documents_indexed=documents_indexed
        )

    except Exception:
        update_status(run_id, "failed")
        raise
