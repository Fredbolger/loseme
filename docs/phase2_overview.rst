Phase 2 – Persistent Vector Search & Qdrant Integration
=======================================================

Phase Goal
----------

Stabilise and harden the system after Phase 1 by introducing a **persistent
vector database (Qdrant)**, aligning ingestion and search with real-world
operation, and clearly separating **test**, **development**, and **runtime**
concerns.

Phase 2 assumes:

- Phase 1 (filesystem ingestion, API, CLI skeleton) is complete
- Docker is the primary execution environment


Entry Criteria
--------------

The following conditions mark the official start of Phase 2:

- Filesystem ingestion endpoint implemented (``/ingest/filesystem``)
- CLI available via ``docker compose run cli``
- Vector store abstraction in place
- All Phase 1 tests passing
- Qdrant service integrated via Docker Compose
- Qdrant persistence verified via Docker volume


Checklist
---------


1. Qdrant Integration (Core)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Add Qdrant service to ``docker-compose.yml``
- Configure persistent volume (``/qdrant/storage``)
- Connect API to Qdrant via Docker DNS (``qdrant:6333``)
- Implement ``QdrantVectorStore``
- Ensure collection existence on startup (no auto-recreate)
- Use Qdrant Query API correctly (``query=`` instead of ``query_vector=``)
- Enforce valid Qdrant point IDs (UUID or unsigned integer)


2. Persistence & Safety
~~~~~~~~~~~~~~~~~~~~~~~

- Verify vector data survives ``docker compose down`` / ``up``
- Guard destructive operations (e.g. ``clear()``) behind an environment flag
- Document collection recreation requirements (embedding size changes)


3. Search Pipeline
~~~~~~~~~~~~~~~~~~

- Store chunk payloads in Qdrant (content, document_id, metadata)
- Implement vector similarity search via Qdrant
- Improve search result formatting (scores, snippets)
- Define default search limits and pagination strategy


4. Testing Strategy
~~~~~~~~~~~~~~~~~~~

- Unit tests for vector store abstraction
- Qdrant-backed integration tests
- Decide whether tests auto-start Qdrant or require manual startup
- Clearly mark Qdrant-dependent tests (e.g. ``@integration``)


5. CLI Hardening
~~~~~~~~~~~~~~~~

- CLI uses Docker DNS for API access (``api:8000``)
- CLI uses same data mount as API (``LOSEME_DATA_DIR``)
- CLI prints meaningful output when no search results are found
- CLI provides clear feedback for ingestion counts and errors


6. Documentation
~~~~~~~~~~~~~~~~

- Docker-based installation documented
- Qdrant persistence model documented
- Phase 2 architecture overview added
- Operational notes included (resetting Qdrant, migrations)


Non-Goals (Out of Scope for Phase 2)
------------------------------------

The following are explicitly deferred to later phases:

- Hybrid (BM25 + vector) search
- Reranking or relevance models
- Authentication or multi-user support
- Production orchestration (Kubernetes, Helm, etc.)


Exit Criteria
-------------

Phase 2 is considered complete when:

- Qdrant is the default vector backend
- Vector data is persistent and safe across restarts
- End-to-end search works via API and CLI
- Documentation reflects actual system behaviour
- Tests clearly distinguish unit vs integration concerns


Notes
-----

- Changing embedding dimensions requires **manual collection recreation**
- ``docker compose down -v`` is the only operation that deletes vector data
- Phase 3 should focus on search quality, ranking, and retrieval improvements

