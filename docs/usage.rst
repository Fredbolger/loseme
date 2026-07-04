Usage
=====

This guide covers how to use LoseMe once it's installed.

--------------------------------------------------------------------------

Web UI
------

The web interface is available at http://localhost:3000 (or your configured port).

**Dashboard Tab**

Overview of indexed content with statistics:

- Total document parts, chunks, source instances, and devices
- List of all monitored sources in a collapsible tree grouped by path prefix
- Each source card shows:
  - Source type (filesystem / thunderbird)
  - File path / locator
  - Document count
  - Last ingested timestamp
  - **Scan** button - triggers re-indexing
  - **Delete** button - removes source and all its vectors

**Search Tab**

Three-column layout for searching and viewing results:

- **Left column**: Ranked result cards with relevance score bars. Click to open.
- **Center column**: Document viewer. Renders plaintext, markdown, PDFs, and emails inline.
- **Right column**: LLM-synthesized answer (if Ollama is configured).

The search bar supports:

- ``Top K`` slider to control number of results
- Model selector (populates from local Ollama instance)

**Supported file previews:**
  ``.txt``, ``.md``, ``.rst``, ``.py``, ``.js``, ``.ts``, ``.css``, ``.html``, ``.pdf``, ``.eml``, Thunderbird emails.

**Runs Tab**

Full visibility into indexing run history:

- Filter by status or source type
- Group by status or source type
- Each run card shows:
  - Run ID and status (with live pulse animation for running jobs)
  - Discovered vs indexed document count with progress bar
  - Stop / Resume / Delete actions

**Storage Tab**

Chunk-level statistics:

- Total document parts and chunks
- Chunker version breakdown
- Histograms of chunk size distribution
- Chunks-per-document distribution
- Filterable by chunker

--------------------------------------------------------------------------

CLI Usage
---------

The CLI runs inside the client container or locally with Poetry.

**Running the CLI:**

.. code-block:: bash

    # From within the client container
    docker compose -f docker-compose.client.yml exec client python -m cli.main
    
    # Or locally
    poetry run python -m client.cli.main

**Indexing Commands:**

**Index a local directory (one-shot):**

.. code-block:: bash

    python -m client.cli.main ingest filesystem /path/to/documents
    
    # With options
    python -m client.cli.main ingest filesystem /path/to/docs \
        --recursive \
        --include-pattern "*.md" \
        --include-pattern "*.txt"
    
    python -m client.cli.main ingest filesystem /path/to/docs \
        --exclude-pattern "*.log" \
        --exclude-pattern "tmp/*"

**Index a Thunderbird mailbox:**

.. code-block:: bash

    python -m client.cli.main ingest thunderbird /path/to/Inbox
    
    # Ignore specific senders
    python -m client.cli.main ingest thunderbird /path/to/Inbox \
        --ignore-from "newsletter@company.com" \
        --ignore-from "*@spam-domain.com"

**Force re-processing:**

.. code-block:: bash

    python -m client.cli.main ingest filesystem /path/to/docs --force-reprocess

**Search Commands:**

**Search for documents:**

.. code-block:: bash

    python -m client.cli.main search "machine learning gradient descent"
    python -m client.cli.main search "project meeting notes" --top-k 20

**Interactive search (open selected file):**

.. code-block:: bash

    python -m client.cli.main search "invoice from acme" --interactive
    # After results are displayed, enter a number to open that file

**Source Management Commands:**

**List all monitored sources:**

.. code-block:: bash

    python -m client.cli.main sources list

**Add sources for persistent monitoring:**

.. code-block:: bash

    python -m client.cli.main sources add filesystem /data/documents
    python -m client.cli.main sources add thunderbird /data/mail/Inbox

**Scan a specific source:**

.. code-block:: bash

    python -m client.cli.main sources scan <source-id>

**Scan all sources:**

.. code-block:: bash

    python -m client.cli.main sources scan-all

**Delete a source:**

.. code-block:: bash

    python -m client.cli.main sources delete <source-id>

**CLI Command Reference:**

.. code-block:: text

    Usage: python -m client.cli.main [OPTIONS] COMMAND

    Commands:
      ingest      Index documents (filesystem or thunderbird)
      search      Search indexed documents
      sources     Manage persistent sources

    Ingest commands:
      filesystem  Index a filesystem directory
      thunderbird Index a Thunderbird mailbox

    Sources commands:
      add         Add a new source
      list        List all sources
      scan        Scan a specific source
      scan-all    Scan all sources
      delete      Delete a source

--------------------------------------------------------------------------

API Usage
---------

The server exposes a REST API on port 8000.

**Authentication:**

If ``LOSEME_API_KEY`` is set, include the header:

.. code-block:: bash

    curl -H "X-API-Key: your-key" http://localhost:8000/health

Exempt paths (no key required): ``/health``, ``/docs``, ``/openapi.json``.

**Key Endpoints:**

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Endpoint
     - Description
   * - ``GET /health``
     - Health check
   * - ``POST /search``
     - Perform semantic search
   * - ``GET /documents/{id}``
     - Get document metadata
   * - ``GET /documents/preview/{id}``
     - Get document preview
   * - ``GET /documents/open/{id}``
     - Get open descriptor for document
   * - ``POST /ingest/document_part``
     - Ingest a document part
   * - ``POST /runs/create``
     - Create a new indexing run
   * - ``POST /runs/start_indexing/{run_id}``
     - Start indexing for a run
   * - ``GET /runs/list``
     - List all indexing runs
   * - ``POST /runs/request_stop/{run_id}``
     - Request stop for a run
   * - ``GET /sources/get_all_sources``
     - List all registered sources

**Search Request Example:**

.. code-block:: bash

    curl -X POST http://localhost:8000/search \
        -H "Content-Type: application/json" \
        -d '{"query": "machine learning", "top_k": 10}'

**Search Response Example:**

.. code-block:: json

    {
        "session_id": "abc123...",
        "results": [
            {
                "chunk_id": "chunk-abc-123",
                "document_part_id": "doc-part-xyz-456",
                "device_id": "my-device",
                "score": 0.8742,
                "metadata": {},
                "source_path": "/path/to/document.pdf",
                "source_type": "filesystem",
                "unit_locator": "page-5",
                "chunk_text": "Machine learning is a field..."
            },
            ...
        ],
        "cache_hit": false,
        "cache_score": null,
        "is_continuation": false
    }

**Full API Documentation:**

For complete API details, see the interactive Swagger/ReDoc documentation:

- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)

--------------------------------------------------------------------------

Search Sessions
--------------

LoseMe implements **search session caching** to avoid re-running similar queries.

When you perform a search:

1. The query is embedded into a vector
2. The system checks for similar previous sessions
3. If a match is found above the threshold (default: 0.95), it returns the cached session
4. A background task refreshes the results in the meantime

This provides instant results for similar queries while keeping data up-to-date.

**Session Management:**

- ``GET /search/history`` - List all search sessions
- ``GET /search/sessions/{session_id}`` - Get session details
- ``DELETE /search/sessions/{session_id}`` - Delete a session
- ``POST /search/sessions/{session_id}/answer`` - Store an LLM answer

--------------------------------------------------------------------------

Chatting with LLM
-----------------

If you have Ollama running locally, the web UI can integrate with it for chat:

**Chat Endpoint:**

.. code-block:: bash

    POST /search/chat
    {
        "session_id": "abc123",
        "message": "Tell me about machine learning",
        "top_k": 10
    }

The response includes:

- Search results (as with regular search)
- Conversation context built from message history
- Previous sources for context

This enables multi-turn conversations with your documents as context.

--------------------------------------------------------------------------

Indexing Runs in Detail
----------------------

Indexing runs track the lifecycle of document ingestion:

**Run Statuses:**

- ``pending`` - Created but not started
- ``running`` - Actively processing documents
- ``discovering_stopped`` - Client finished discovering, server still processing
- ``completed`` - All documents processed successfully
- ``interrupted`` - Stopped by user request
- ``failed`` - Failed due to error

**Run Lifecycle:**

1. Client creates run: ``POST /runs/create``
2. Client starts indexing: ``POST /runs/start_indexing/{run_id}``
3. Client queues document parts: ``POST /ingest/document_part``
4. Server processes queue in background
5. Client signals discovery complete: ``POST /runs/discovering_stopped/{run_id}``
6. Server marks complete when queue is empty

**Run Statistics:**

Each run tracks:

- ``discovered_document_count`` - Number of document parts discovered
- ``indexed_document_count`` - Number successfully indexed
- ``last_document_id`` - Most recent document processed
- ``stop_requested`` - Whether user requested stop
- ``is_discovering`` - Whether client is still discovering
- ``is_indexing`` - Whether server is still processing

--------------------------------------------------------------------------

Preview System
--------------

LoseMe includes a preview system for rendering documents in the web UI:

**Supported Types:**

- Plain text files (``.txt``, ``.md``, ``.rst``)
- Code files (``.py``, ``.js``, ``.ts``, ``.css``, ``.html``)
- PDF files (rendered as HTML with highlighted matches)
- Email files (``.eml``)
- Thunderbird mailbox messages

**Preview Endpoints:**

- ``GET /documents/preview/{document_part_id}`` - Get HTML preview
- ``GET /documents/serve/{document_part_id}`` - Get raw file bytes

The preview system uses source-specific generators to render content appropriately.

--------------------------------------------------------------------------

Maintenance Operations
-----------------------

**Clean up old runs:**

.. code-block:: bash

    # List all runs
    curl http://localhost:8000/runs/list
    
    # Delete a specific run
    curl -X POST http://localhost:8000/runs/delete/<run_id>
    
    # Stop all runs
    curl -X POST http://localhost:8000/runs/stop_all

**Clear all data:**

.. code-block:: bash

    # Clear all indexing runs
    curl "http://localhost:8000/runs/clear_all_runs?confirm=true"
    
    # Clear vector store (requires ALLOW_VECTOR_CLEAR=1)
    # Set in environment and restart server

**Repair migrations:**

.. code-block:: bash

    # Inside server container
    python -m scripts.repair_chunker_migration
    python -m scripts.audit_orphan_chunks

**Inspect chunks:**

.. code-block:: bash

    python -m scripts.inspect_chunks
