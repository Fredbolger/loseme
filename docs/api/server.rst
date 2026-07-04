Server API
==========

The server provides a REST API built with FastAPI. All endpoints are 
accessible at the server's base URL (default: http://localhost:8000).

For interactive API documentation, see:

- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)

This page provides an overview of the server API structure.

--------------------------------------------------------------------------

Base URL
-------

All API endpoints are relative to the server's base URL.

In Docker Compose, use ``http://server:8000`` from within the Docker network.
From the host machine, use ``http://localhost:8000``.

In production, the base URL should be configured via ``LOSEME_API_URL``.

--------------------------------------------------------------------------

Authentication
--------------

If ``LOSEME_API_KEY`` is set on the server, all requests (except exempt paths) 
must include the API key in the ``X-API-Key`` header:

.. code-block:: bash

    curl -H "X-API-Key: your-secret-key" http://localhost:8000/search

**Exempt paths** (no authentication required):

- ``GET /health``
- ``GET /docs``
- ``GET /openapi.json``

--------------------------------------------------------------------------

Endpoints
--------

Health
~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - ``GET /health``
     - Health check. Returns server status and version.

Search
~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - ``POST /search``
     - Perform semantic search. Returns ranked results with scores.
   * - ``POST /search/chat``
     - Chat endpoint with conversation context. Returns results + context.
   * - ``GET /search/history``
     - List all search sessions.
   * - ``GET /search/sessions/{session_id}``
     - Get details for a specific session.
   * - ``DELETE /search/sessions/{session_id}``
     - Delete a search session.
   * - ``POST /search/sessions/{session_id}/answer``
     - Store an LLM answer in the session.
   * - ``POST /search/sessions/{session_id}/vector_result``
     - Store vector search result as assistant message.

Documents
~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - ``GET /documents/{document_part_id}``
     - Get document part metadata.
   * - ``GET /documents/by_id/{document_id}``
     - Get document by ID (alias).
   * - ``GET /documents/preview/{document_part_id}``
     - Get HTML preview of document.
   * - ``GET /documents/serve/{document_part_id}``
     - Get raw file bytes.
   * - ``GET /documents/open/{document_part_id}``
     - Get open descriptor (how to open the document).
   * - ``GET /documents/stats``
     - Get document statistics.
   * - ``GET /documents/stats/per_source``
     - Get statistics grouped by source.
   * - ``GET /documents/stats/chunker``
     - Get chunker-specific statistics.
   * - ``POST /documents/batch_get``
     - Get multiple document parts by ID.
   * - ``POST /documents/add_discovered_document_part``
     - Mark a document as discovered but not yet indexed.
   * - ``GET /documents/get_all_document_parts``
     - List all document parts.

Ingest
~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - ``POST /ingest/document_part``
     - Ingest a document part for processing.

Chunks
~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - ``GET /chunks/count``
     - Get total chunk count.
   * - ``GET /chunks/by_source``
     - Get chunks grouped by source.

Runs
~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - ``POST /runs/create``
     - Create a new indexing run.
   * - ``POST /runs/start_indexing/{run_id}``
     - Start indexing for a run (triggers background processing).
   * - ``POST /runs/resume/{run_id}``
     - Resume an interrupted run.
   * - ``POST /runs/stop_latest/{source_type}``
     - Stop the latest run for a source type.
   * - ``POST /runs/request_stop/{run_id}``
     - Request stop for a specific run.
   * - ``POST /runs/delete/{run_id}``
     - Delete an indexing run.
   * - ``POST /runs/stop_all``
     - Stop all indexing runs.
   * - ``POST /runs/mark_completed/{run_id}``
     - Mark a run as completed.
   * - ``POST /runs/mark_failed/{run_id}``
     - Mark a run as failed.
   * - ``POST /runs/mark_interrupted/{run_id}``
     - Mark a run as interrupted.
   * - ``POST /runs/discovering_stopped/{run_id}``
     - Mark that client has stopped discovering.
   * - ``GET /runs/list``
     - List all indexing runs.
   * - ``GET /runs/is_stop_requested/{run_id}``
     - Check if stop was requested for a run.
   * - ``GET /runs/is_discovering/{run_id}``
     - Check if a run is still discovering.
   * - ``GET /runs/resume_latest/{source_type}``
     - Get the latest interrupted run for a source type.
   * - ``POST /runs/increment_discovered/{run_id}``
     - Increment discovered document count.
   * - ``GET /runs/clear_all_runs``
     - Clear all run records (requires confirmation).

Queue
~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - ``POST /queue/add``
     - Add a document part to the processing queue.
   * - ``GET /queue/next/{run_id}``
     - Get the next document part from queue for a run.
   * - ``POST /queue/remove/{run_id}/{document_part_id}``
     - Remove a document part from the queue.
   * - ``GET /queue/status/{run_id}``
     - Get queue status for a run.

Sources
~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - ``POST /sources/add``
     - Register a new source.
   * - ``GET /sources/get_all_sources``
     - List all registered sources.
   * - ``POST /sources/scan/{source_id}``
     - Trigger a scan for a specific source.
   * - ``DELETE /sources/delete/{source_id}``
     - Delete a source.

Database
~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - ``GET /database/stats``
     - Get database statistics.
   * - ``POST /database/clear``
     - Clear the database (requires confirmation).

LLM Integration
~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - ``POST /llm/generate``
     - Generate text using an LLM.
   * - ``GET /llm/models``
     - List available LLM models.

--------------------------------------------------------------------------

Request/Response Schemas
------------------------

For complete request and response schemas, see the interactive API documentation 
at http://localhost:8000/docs.

Key schemas include:

- ``SearchRequest``: query, top_k, cache_threshold, session_id
- ``ChatRequest``: session_id, message, top_k
- ``IngestDocumentPartRequest``: run_id, document_part_id, source_type, checksum, etc.
- ``IndexingRun``: id, scope, start_time, status, discovered_document_count, etc.

--------------------------------------------------------------------------

Error Handling
--------------

Errors are returned with appropriate HTTP status codes:

- ``400 Bad Request`` - Invalid request data
- ``401 Unauthorized`` - Missing or invalid API key
- ``404 Not Found`` - Resource not found
- ``422 Unprocessable Entity`` - Validation error
- ``500 Internal Server Error`` - Server-side error

Error responses include a ``detail`` field with a human-readable message:

.. code-block:: json

    {
        "detail": "Document with ID xyz not found"
    }

--------------------------------------------------------------------------

Rate Limiting and Timeouts
--------------------------

The server does not currently implement rate limiting. For production use, 
consider adding a rate limiter or using a reverse proxy (Nginx, Traefik) with 
rate limiting configured.

Default timeouts:

- API request timeout: 30 seconds
- Embedding generation: depends on model
- Search query: typically < 1 second for Qdrant

--------------------------------------------------------------------------

WebSocket Support
-----------------

The server does not currently expose WebSocket endpoints. All communication 
is via REST/HTTP.

Future API enhancements may include WebSocket support for:

- Real-time search result streaming
- Progress updates for indexing runs
- Event notifications

--------------------------------------------------------------------------

Versioning
---------

The API is currently at version 1.0. Version information is available in 
the OpenAPI schema at ``/openapi.json``.

Breaking changes will be documented in the changelog and will result in a 
major version bump (v2.0, etc.).
