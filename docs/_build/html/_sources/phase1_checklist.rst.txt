Phase 1: Checklist
------------------

.. list-table::
   :header-rows: 1
   :widths: 20 10 70

   * - Task
     - Status
     - Description
   * - Repository & Infrastructure
     - ✅ Done
     - Folder structure, .gitignore, Docker Compose
   * - API Dockerfile
     - ✅ Done
     - Dockerfile for FastAPI service: Dependencies, entrypoint, health check
   * - SQLite / Qdrant volumes
     - ⬜ To do
     - Ensure persistence for metadata DB and vector DB
   * - Core Data Model
     - ✅ Done
     - Document & Chunk models, metadata fields
   * - Versioning / downstream integration
     - ⬜ To do
     - Strategy for device identifiers, versioning
   * - Filesystem Collector
     - ✅ Partially Done
     - Directory traversal, file type filtering, text extraction, metadata capture
   * - Chunking Module
     - ⬜ To do
     - Chunk size, paragraph splitting, overlap, chunk IDs, document references: 500–700 tokens, 10–20% overlap
   * - Preserve document context
     - ⬜ To do
     - Maintain references across chunks
   * - Embedding Module
     - ✅ Partially Done
     - SentenceTransformers integration, model loading, batch processing, edge case handling
   * - Storage Layer – Vector DB
     - ✅ Done
     - In-memory vector store
   * - Persistent vector DB (Qdrant)
     - ⬜ To do
     - Integration with Qdrant for persistent storage of embeddings and metadata
   * - Storage Layer – Metadata DB
     - ✅ Done
     - SQLite tables for documents and chunks
   * - Query optimization
     - ⬜ To do
     - Indexing strategies if needed
   * - API Layer
     - ✅ Partially Done
     - FastAPI setup, ingestion endpoint, search endpoint, ranked results, metadata filtering
   * - Wire ingestion & search endpoints
     - ⬜ To do
     - Connect collector, chunker, embedder, storage to API and DB
   * - Metadata filtering / sqagger
     - ⬜ To do
     - Implement metadata-based filtering in search
   * - CLI Client
     - ⬜ To do
     - Typer-based CLI with ingest and search commands, result display, error handling
   * - Testing
     - ✅ Partially Done
     - Ingestion tests, search tests, manual relevance tests, document limitations
   * - Document limitations and edge cases
     - ⬜ To do
     - Document known limitations and edge cases
