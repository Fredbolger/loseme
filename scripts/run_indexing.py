"""
End-to-end Phase 1 indexing runner.

This script wires together:
- Filesystem ingestion
- Simple chunking
- Dummy embeddings
- In-memory vector store

Run this BEFORE adding FastAPI.
"""

from pathlib import Path

from collectors.filesystem.filesystem_source import FilesystemIngestionSource
from pipeline.chunking.simple_chunker import SimpleTextChunker
from pipeline.embeddings.dummy import DummyEmbeddingProvider
from storage.vector_db.in_memory import InMemoryVectorStore
from src.domain.models import IndexingScope


def main():
    # ---- CONFIG ----
    scope = IndexingScope(
        directories=[Path("./docs")],
        include_patterns=["*.md", "*.txt"],
        exclude_patterns=[],
    )

    # ---- COMPONENTS ----
    ingestion = FilesystemIngestionSource()
    chunker = SimpleTextChunker(chunk_size=500, overlap=50)
    embedder = DummyEmbeddingProvider(dimension=384)
    vector_store = InMemoryVectorStore(dimension=embedder.dimension())

    # ---- INDEXING ----
    print("Starting indexing run…")

    document_ids = ingestion.list_documents(scope)
    print(f"Found {len(document_ids)} documents")

    total_chunks = 0

    for doc_id in document_ids:
        document = ingestion.read_document(doc_id)

        if not document.path or not document.path.exists():
            continue

        with open(document.path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()

        chunks = chunker.chunk(document, text)

        for chunk in chunks:
            vector = embedder.embed(chunk.content)
            vector_store.add(chunk, vector)

        total_chunks += len(chunks)

    print(f"Indexed {total_chunks} chunks")

    # ---- TEST QUERY ----
    query = "architecture"
    query_vector = embedder.embed(query)
    results = vector_store.query(query_vector, top_k=5)

    print("\nTop results for query:", query)
    for chunk_id, score, metadata in results:
        print(f"- {chunk_id[:8]}… score={score:.4f} metadata={metadata}")


if __name__ == "__main__":
    main()
