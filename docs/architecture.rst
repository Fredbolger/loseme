Architecture
============

LoseMe follows a **client-server architecture** with clear separation of concerns.
The system is designed to be:

- **Local-first**: All processing happens on your own hardware
- **Extensible**: New sources, chunkers, and embeddings can be added easily
- **Resumable**: Indexing can be stopped and resumed safely
- **Deterministic**: Reproducible IDs ensure no duplicate indexing

--------------------------------------------------------------------------

System Overview
---------------

::

    +---------------+     +----------------+     +----------------+
    |               |     |                |     |                |
    |   CLI/Web UI  +---->+   API Server    +---->+   Qdrant       |
    |   (Client)    |     |   (Server)     |     |   (Vector DB) |
    |               |     |                |     |                |
    +---------------+     +--------+-------+     +----------------+
                                   |
                                   v
                          +--------+-------+
                          |                |
                          |   SQLite       |
                          |   (Metadata)   |
                          |                |
                          +----------------+

**Client Container**
  - CLI for ingestion and search
  - Web UI for dashboard and search
  - Document extractors (PDF, HTML, plaintext, EML, Thunderbird, Python)
  - Filesystem and Thunderbird ingestion sources

**Server Container**
  - FastAPI REST API
  - Pipeline: chunking and embedding
  - Metadata storage: SQLite
  - Vector storage: Qdrant

**Core Package** (shared)
  - Domain models (Document, DocumentPart, Chunk, IndexingRun)
  - ID generation utilities
  - Configuration

--------------------------------------------------------------------------

Containers and Deployment
------------------------

LoseMe is deployed using Docker Compose with separate containers:

**core**
  Shared Python library. Built first and installed into both client and server.

**server**
  FastAPI application with GPU support (NVIDIA runtime). Exposes API on port 8000.
  Requires Qdrant as a dependency.

**client**
  Web UI and CLI. Exposes web interface on port 3000. Mounts host directories
  for file access.

**qdrant**
  Vector database service. Stores embeddings with metadata. Exposes on port 6333.

Code locations::

    core/                # Shared package (loseme-core)
    server/             # Server container with API and pipeline
    client/             # Client container with CLI and web UI

--------------------------------------------------------------------------

Data Flow
---------

**Ingestion:**

1. Client discovers documents (filesystem walk or Thunderbird mbox reading)
2. Extractors pull text and metadata from files/emails
3. Client sends document parts to server via POST /ingest/document_part
4. Server chunks text using configured chunker (simple/sentence/semantic)
5. Server generates embeddings using configured embedding model
6. Server stores chunks + embeddings in Qdrant
7. Server stores metadata in SQLite

**Search:**

1. User sends query to POST /search
2. Server embeds query using same embedding model
3. Server queries Qdrant for nearest neighbor chunks
4. Server returns ranked results with similarity scores
5. Client can preview or open original documents

**Indexing Run Lifecycle:**

1. POST /runs/create - creates run with scope
2. POST /runs/start_indexing/{run_id} - marks as running, starts background processing
3. Client queues document parts to /ingest/document_part
4. Server processes queue in background task
5. POST /runs/discovering_stopped/{run_id} - marks discovery complete
6. Run continues until queue empty, then marks as completed

--------------------------------------------------------------------------

Component Layers
----------------

**Core Layer** (``core/loseme_core/``)
  Domain models and utilities shared by client and server:

  - **models.py**: Document, DocumentPart, Chunk, IndexingRun, IngestionSource
  - **document_models.py**: Core data structures
  - **domain.py**: EmbeddingOutput, EmbeddingProvider abstract interface
  - **config.py**: Configuration constants (CHUNKER_TYPE, EMBEDDING_MODEL, etc.)
  - **ids.py**: Deterministic ID generation
  - **scope_models.py**: IndexingScope base class

**Client Layer** (``client/``)
  Document discovery and extraction:

  - **extractors/**: Content extractors for different file types
  - **sources/**: Document source handlers (filesystem, thunderbird)
  - **ingest/**: Queue client for sending parts to server
  - **cli/**: Typer-based CLI commands
  - **web/**: FastAPI web frontend
  - **preview/**: Document preview generators

**Server Layer** (``server/``)
  API and processing pipeline:

  - **api/app/**: FastAPI application and routes
  - **pipeline/**: Chunking and embedding
  - **storage/**: Metadata and vector storage
  - **preview/**: Server-side preview generators
  - **wiring.py**: Factory functions for component assembly

--------------------------------------------------------------------------

Design Principles
-----------------

**Local-first**
  No cloud API calls during indexing or search. Everything runs on your hardware.

**Stable, deterministic IDs**
  The deduplication strategy relies on reproducible IDs:

  - ``source_instance_id``: source_type + device_id + source_path
  - ``logical_document_part_id``: source_instance_id + unit_locator
  - ``chunk_id``: document_part_id + checksum + chunk index

  A change to any input produces a new ID, triggering re-indexing.

**Multi-device awareness**
  The same file on two devices gets separate embeddings, tracked by device_id.
  This prevents duplicates without requiring a shared filesystem.

**Resumable indexing**
  Runs move through a state machine: pending -> running -> discovering_stopped -> 
  completed/interrupted/failed. Interrupted runs resume without reprocessing.

**Skip-on-reingest**
  A document part is skipped if its checksum, extractor name/version, and chunker 
  name/version are all unchanged since the last run.

**Replaceable components**
  Each major component (chunker, embedder, vector store) is behind an interface
  and can be swapped without affecting the rest of the system.

--------------------------------------------------------------------------

Extensibility Points
--------------------

**Adding a new source type:**
  1. Create a new scope model in core (e.g., ``MySourceIndexingScope``)
  2. Create a new ingestion source in client/sources/
  3. Register it in the ingestion_source_registry
  4. Add client CLI commands

**Adding a new extractor:**
  1. Implement DocumentExtractor in client/extractors/
  2. Register it in extractor_registry

**Adding a new chunker:**
  1. Implement chunker in server/pipeline/chunking/
  2. Add to wiring.py build_chunker()
  3. Set LOSEME_CHUNKER environment variable

**Adding a new embedding model:**
  1. Implement EmbeddingProvider in server/pipeline/embeddings/
  2. Add to wiring.py build_embedding_provider()
  3. Set LOSEME_EMBEDDING_MODEL environment variable

