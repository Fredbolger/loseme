import warnings
import os
from src.domain.models import IndexingScope
from collectors.filesystem.filesystem_source import FilesystemIngestionSource
from storage.metadata_db.indexing_runs import create_run, load_latest_run
from storage.metadata_db.processed_documents import is_processed, mark_processed
from storage.metadata_db.db import init_db
from src.core.wiring import build_extractor_registry
from pipeline.chunking.simple_chunker import SimpleTextChunker as Chunker
from pipeline.embeddings.sentence_transformer import SentenceTransformerEmbeddingProvider
from dataclasses import dataclass
from storage.vector_db.runtime import get_vector_store
from storage.metadata_db.document import upsert_document
from storage.metadata_db.indexing_runs import update_status
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


extractor_registry = build_extractor_registry()

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
    chunker = Chunker()
    embedding_provider = SentenceTransformerEmbeddingProvider()
    vector_store = get_vector_store()
    
    if embedding_provider.dimension() != vector_store.dimension():
        raise RuntimeError("Embedding dimension mismatch with vector store")

    '''
    if resume:
        run = load_latest_run("filesystem", scope)
        if run is None:
            raise RuntimeError("Resume=True but no previous run exists for the given scope.")
    else:
        run = create_run("filesystem", scope)
    '''

    documents_discovered = 0
    documents_indexed = 0
    
    update_status(run_id, "running")

    try:
        for doc in source.list_documents():
            if stop_after is not None and documents_discovered >= stop_after:
                raise IngestionCancelled("Ingestion stopped after reaching the stop_after limit.")    
            documents_discovered += 1

            if is_processed(run_id, doc.source_id, doc.checksum):
                logger.info(f"Document at {doc.path} already processed with same checksum, skipping.")
                continue
        
            document_extraction = extractor_registry.extract(Path(doc.docker_path))
            if document_extraction is None:
                warnings.warn(f"No extractor found for document at {doc.path}, skipping.")
                continue

            upsert_document(doc)
            
            chunks, chunk_texts = chunker.chunk(doc,document_extraction.text)
            embeddings = [embedding_provider.embed_query(text) for text in chunk_texts]
            for chunk, embedding in zip(chunks, embeddings):
                vector_store.add(chunk, embedding)

            mark_processed(run_id, doc.source_id, doc.checksum)
            documents_indexed += 1
        update_status(run_id, "completed")
        logger.info(f"Ingestion run {run_id} completed successfully.")
    except Exception:
        update_status(run_id, "interrupted")
        raise
    
    return IngestionResult(
        run_id=run_id,
        status="completed",
        documents_discovered=documents_discovered,
        documents_indexed=documents_indexed
    )

