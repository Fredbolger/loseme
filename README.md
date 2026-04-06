# Local Semantic Memory

> Privacy-preserving semantic search over your personal files — runs entirely on your own hardware.

---

## Overview

Local Semantic Memory lets you search your documents, emails, and notes by **meaning** rather than keywords or filenames. It acts as a semantic index layer on top of your existing files: the original files stay where they are and can be opened directly from search results.

The system is built for people who want full control over their data. All processing — embedding, indexing, and search — happens on your machine. Nothing is sent to external services.

---

## How It Works

```
Filesystem → Extraction → Chunking → Embedding → Vector DB → Search
```

1. **Discovery** — A `Source` (e.g. a filesystem directory) yields `Document` objects for each file.
2. **Extraction** — A global `ExtractorRegistry` maps file types (PDF, DOCX, TXT, …) to content extractors. Unrecognised types are skipped.
3. **Multipart splitting** — Sources that support it (e.g. email with attachments) split documents into `DocumentPart` objects, each indexed independently.
4. **Chunking** — Each `DocumentPart` is split into smaller chunks by a `Chunker` (simple sliding-window or semantic boundary-aware).
5. **Embedding** — Chunks are converted to vector embeddings and stored in [Qdrant](https://qdrant.tech/). Metadata and run state are persisted in SQLite.
6. **Search** — A query is embedded and compared against stored vectors via cosine similarity. Results link back to the original files.
7. **Re-ranking** *(optional)* — Depending on the embedding provider, a second-pass re-ranker can improve result ordering.

---

## Key Design Decisions

### Local-first
All data stays on your devices. No cloud API calls are made during indexing or search.

### Multi-device awareness
The same document on two devices is tracked separately using a `source_instance_id` composed of `source_type`, `device_id`, and `source_path`. This prevents duplicate embeddings across devices without requiring a shared network filesystem.

### Stable, deterministic IDs
The entire deduplication strategy depends on IDs being deterministic:

| ID | Composed from |
|----|--------------|
| `source_instance_id` | `source_type` + `device_id` + `source_path` |
| `logical_document_part_id` | `source_instance_id` + `unit_locator` |
| `chunk_id` | `logical_document_part_id` + `checksum` + chunk index |

A change to any input produces a new ID, which triggers re-indexing of that content and cleanup of stale vectors.

### Resumable indexing
Each indexing run moves through a well-defined state machine (`pending → running → discovering_stopped → completed / failed`). Interrupted runs can be resumed without reprocessing already-indexed documents.

---

## Quick Start

**Prerequisites:** Docker, Docker Compose, Python 3.11+, [Poetry](https://python-poetry.org/)

The deployment is split into two independent stacks: a **server** (API + Qdrant, ideally a machine with a GPU) and a **client** (web frontend, runs on any device that can reach the server).

### Server

```bash
# Copy and fill in the required variables
cp .env.server.example .env.server

# Start Qdrant and the API server
docker compose -f docker-compose.server.yml up -d
```

### Client

```bash
# Copy and fill in the server URL and host data root
cp .env.client.example .env.client

# Start the web client
docker compose -f docker-compose.client.yml up -d
```

### CLI

```bash
# Index a directory
poetry run python -m clients.cli.main ingest /path/to/your/documents

# Search
poetry run python -m clients.cli.main search "machine learning concepts" --top-k 5

# Interactive search (opens the selected file)
poetry run python -m clients.cli.main search "project notes" --interactive
```

---

## Project Structure

```
.
├── src/
│   ├── core/           # IDs, shared utilities
│   └── sources/        # Filesystem and other source adapters
├── pipeline/
│   ├── chunking/       # SimpleTextChunker, SemanticChunker
│   └── embeddings/     # Embedding provider interface and implementations
├── storage/
│   ├── metadata_db/    # SQLite: runs, document parts, checksums
│   └── vector_db/      # Qdrant client, in-memory store for testing
├── api/                # FastAPI server
├── clients/
│   ├── cli/            # Command-line interface
│   └── web/            # Web frontend
├── tests/              # Test suite (see below)
└── docker-compose.yml
```

---

## Configuration

Configuration is split across two env files.

**`.env.server`** — consumed by `docker-compose.server.yml`:

| Variable | Description | Default |
|----------|-------------|---------|
| `LOSEME_DEVICE_ID` | Unique identifier for this machine | `server` |
| `LOSEME_CONTAINER_ROOT` | Path inside the container where user data is mounted | *(empty)* |
| `QDRANT_URL` | Qdrant instance URL | `http://qdrant:6333` |

**`.env.client`** — consumed by `docker-compose.client.yml`:

| Variable | Description | Default |
|----------|-------------|---------|
| `LOSEME_HOST_ROOT` | Host path to mount as `/mnt/userdata` in the client container | *(required)* |

---

## Testing

The test suite covers the full ingestion-to-search pipeline without requiring a live Qdrant instance. An `InMemoryVectorStore` and `DummyEmbeddingProvider` are injected for all tests.

```bash
poetry run pytest
```

Key test modules:

| File | What it covers |
|------|----------------|
| `test_id_stability.py` | ID determinism — the foundation of deduplication |
| `test_ingest_skip_logic.py` | Skip unchanged docs; reprocess on checksum/extractor/chunker change |
| `test_chunker_contracts.py` | `SimpleTextChunker` and `SemanticChunker` invariants |
| `test_search_round_trip.py` | Full vertical slice: ingest → vector store → search API |
| `test_run_lifecycle.py` | Indexing run state machine transitions |

---

## Tech Stack

- **Python 3.11+**
- **FastAPI** — REST API
- **Qdrant** — Vector database
- **SQLite** — Metadata and run state
- **Celery** — Async task processing
- **Docker / Docker Compose** — Deployment

---

## License

Licensed under the [GNU AGPLv3](https://www.gnu.org/licenses/agpl-3.0.en.html).
