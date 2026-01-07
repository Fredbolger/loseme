Phase 1: Semantic Memory MVP
============================

Goal
----

Create a fully local semantic memory system for text-based files. Phase 1 is intentionally limited in scope to enable rapid development and validation of core concepts.

Scope
-----

- Filesystem ingestion (Markdown, TXT, PDF)
- Text chunking
- Local embedding generation
- Metadata storage in SQLite
- Vector storage 
- Search API (basic)
- CLI client (TBD)
- Dockerized environment

Out of Scope
------------
- Images and OCR
- LLM-based summaries or tags
- Multi-device sync
- Email ingestion

Completed
---------

- Repository structure
- Docker Compose setup with API and Qdrant
- Core Pydantic models (Document, Chunk, IndexingScope)
- Filesystem collector for text files
- Dummy embedding provider
- Metadata DB tables
- Basic ingestion API endpoints
- Tests for ingestion and resume logic

Remaining Tasks
---------------

- PDF extraction and metadata timestamps
- Simple chunking module
- Real embeddings (SentenceTransformers)
- Vector storage in Qdrant
- Vector search endpoint
- CLI client commands
- Search integration tests
- Proper paragraph-based chunking

