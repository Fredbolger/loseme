import warnings
import os
from src.domain.models import IndexingScope
from collectors.filesystem.filesystem_source import FilesystemIngestionSource
from collectors.thunderbird.thunderbird_source import ThunderbirdIngestionSource
from storage.metadata_db.indexing_runs import create_run, load_latest_run
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

def ingest_filesystem_scope(scope: IndexingScope, run_id: str, resume: bool = True, stop_after: int | None = None) -> IngestionResult:
    if stop_after is not None:
        warnings.warn("The 'stop_after' parameter is set, which will intentionally limit the number of documents processed. This is for testing purposes only and should not be used in production.", UserWarning)    

    init_db()
    logger.info(f"Starting ingestion for scope: {scope} with run_id: {run_id}, resume={resume}")

    source = FilesystemIngestionSource(scope, extractor_registry)
    vector_store = get_vector_store()
    
    if embedding_provider.dimension() != vector_store.dimension():
        raise RuntimeError("Embedding dimension mismatch with vector store")

    if resume:
        run = load_latest_run("filesystem", scope)
        if run is None:
            raise RuntimeError("Resume=True but no previous run exists for the given scope.")
    else:
        run = create_run("filesystem", scope)

    documents_discovered = len(list(source.list_documents()))
    documents_indexed = 0
    
    update_status(run_id, "running")

    try:
        for idx, doc in enumerate(source.list_documents()):
            logger.debug(f"Discovered document at {doc.source_path}")
            if stop_after is not None and idx >= stop_after:
                raise IngestionCancelled("Ingestion stopped after reaching the stop_after limit.")    
                #logger.info(f"Stopping ingestion after {stop_after} documents as per stop_after limit.")

            if is_processed(doc.source_id, doc.checksum):
                logger.info(f"Document at {doc.source_path} already processed with same checksum, skipping.")
                continue
             
            logical_path = Path(base_path).joinpath(doc.source_path.lstrip("/"))
            document_extraction = extractor_registry.extract(logical_path)
            upsert_document(doc)
            
            chunks, chunk_texts = chunker.chunk(doc,document_extraction.text)
            # If the emebedding provider supports document embedding, use it here
            if hasattr(embedding_provider, "embed_document"):
                logger.debug("Using instruction based document embedding.")
                embeddings = [embedding_provider.embed_document(text) for text in chunk_texts]
            else:
                embeddings = [embedding_provider.embed_query(text) for text in chunk_texts]
            for chunk, embedding in zip(chunks, embeddings):
                vector_store.add(chunk, embedding)

            mark_processed(run_id, doc.source_id, doc.checksum)
            documents_indexed += 1
        update_status(run_id, "completed")
        logger.info(f"Ingestion run {run_id} completed successfully. Discovered {documents_discovered} documents, indexed {documents_indexed} documents.")
    except Exception:
        update_status(run_id, "interrupted")
        raise
    
    return IngestionResult(
        run_id=run_id,
        status="completed",
        documents_discovered=documents_discovered,
        documents_indexed=documents_indexed
    )

