# LoseMe — Local Semantic Memory

> Privacy-preserving semantic search over your personal files. Runs entirely on your own hardware.

---

## What It Does

LoseMe lets you search documents, emails, and notes by **meaning** rather than filename or keyword. It builds a semantic index on top of your existing files — originals stay where they are and can be opened directly from search results.

All processing (embedding, indexing, search) happens on your machine. Nothing is sent to external services.

---

## Architecture

```
Filesystem / Thunderbird
        │
        ▼
   [Client Container]
   Extraction → Queue → API
        │
        ▼
   [Server Container]
   Chunking → Embedding → Qdrant (vector DB)
                       → SQLite (metadata)
        │
        ▼
   Search API → Web UI / CLI
```

The system is split into two independent stacks:

| Component | Role |
|-----------|------|
| **Server** | FastAPI + Qdrant + SQLite. Handles chunking, embedding, vector search. Ideally a machine with a GPU. |
| **Client** | Web frontend + CLI. Runs on any device that can reach the server. Reads local files, talks to server for indexing and search. |
| **Core** | Shared Python package (`loseme-core`) with models, IDs, and config. Installed into both containers. |

### Key Design Decisions

**Local-first.** No cloud API calls during indexing or search.

**Stable, deterministic IDs.** The deduplication strategy relies entirely on IDs being reproducible:

| ID | Inputs |
|----|--------|
| `source_instance_id` | `source_type` + `device_id` + `source_path` |
| `logical_document_part_id` | `source_instance_id` + `unit_locator` |
| `chunk_id` | `document_part_id` + `checksum` + chunk index |

A change to any input produces a new ID, triggering re-indexing and stale vector cleanup.

**Multi-device awareness.** The same file on two devices gets separate embeddings, tracked by `device_id`. This prevents duplicates without requiring a shared filesystem.

**Resumable indexing.** Runs move through a state machine (`running → discovering_stopped → completed / interrupted / failed`). Interrupted runs resume without reprocessing already-indexed documents.

**Skip-on-reingest.** A document part is skipped if its checksum, extractor name/version, and chunker name/version are all unchanged since the last run.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI |
| Vector DB | Qdrant |
| Metadata / Runs | SQLite |
| Embedding (default) | `sentence-transformers/all-MiniLM-L6-v2` |
| Embedding (optional) | BGE-M3 (hybrid dense + sparse + ColBERT), Nomic |
| Chunking | Simple sliding-window, Sentence-aware, Semantic (embedding-based) |
| LLM Answer (Web UI) | Ollama (local, streaming) |
| Deployment | Docker / Docker Compose |
| Language | Python 3.11+ |

---

## Project Structure

```
.
├── core/                   # Shared Python package (loseme-core)
│   └── loseme_core/        # IDs, models, config, scope definitions
│
├── server/                 # Server container
│   ├── api/app/            # FastAPI app, routes
│   ├── pipeline/
│   │   ├── chunking/       # SimpleTextChunker, SentenceAwareChunker, SemanticChunker
│   │   └── embeddings/     # SentenceTransformer, Nomic, BGE-M3, Dummy
│   ├── storage/
│   │   ├── metadata_db/    # SQLite: runs, document parts, migrations
│   │   └── vector_db/      # Qdrant store, in-memory store (for tests)
│   └── preview/            # Server-side preview generators
│
├── client/                 # Client container
│   ├── cli/                # Typer CLI (ingest, sources, search)
│   ├── extractors/         # PDF, plaintext, HTML, EML, Thunderbird, Python extractors
│   ├── sources/
│   │   ├── filesystem/     # FilesystemIngestionSource
│   │   └── thunderbird/    # ThunderbirdIngestionSource
│   ├── preview/            # Client-side preview generators
│   └── web/                # Web frontend (vanilla JS, no framework)
│       └── static/
│           ├── app.js      # Router, API client, theme
│           ├── views/      # Dashboard, Search, Runs, Storage tab logic
│           ├── previews/   # PDF, email, plaintext renderers
│           └── styles/     # CSS (base, layout, components, search, runs, animations)
│
└── tests/                  # Test suite
```

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- NVIDIA GPU (recommended for embedding speed; CPU works but is slow)

---

### 1. Server Setup

```bash
cp .env.server.example .env.server
# Edit .env.server — set LOSEME_DEVICE_ID at minimum

docker compose -f docker-compose.server.yml build
docker compose -f docker-compose.server.yml up -d
```

The server exposes the API on port `8000` and Qdrant on port `6333`.

**`.env.server` variables:**

| Variable | Description | Default |
|----------|-------------|---------|
| `LOSEME_DEVICE_ID` | Unique name for this machine | `server` |
| `QDRANT_URL` | Qdrant instance URL | `http://qdrant:6333` |
| `LOSEME_EMBEDDING_MODEL` | Embedding model to use | `sentence-transformer:all-MiniLM-L6-v2` |
| `LOSEME_CHUNKER` | Chunker type: `simple`, `sentence`, `semantic` | `simple` |
| `LOSEME_API_KEY` | Optional API key for auth | *(empty = disabled)* |

---

### 2. Client Setup

```bash
cp .env.client.example .env.client
# Edit .env.client — set LOSEME_HOST_ROOT and LOSEME_API_URL

docker compose -f docker-compose.client.yml build
docker compose -f docker-compose.client.yml up -d
```

The client exposes the web UI on port `3000`.

**`.env.client` variables:**

| Variable | Description |
|----------|-------------|
| `LOSEME_HOST_ROOT` | Host path mounted as `/mnt/userdata` inside the container (your files live here) |
| `LOSEME_CONTAINER_ROOT` | Container path for the mount (usually `/mnt/userdata`) |
| `LOSEME_API_URL` | URL of the server API | 
| `LOSEME_DEVICE_ID` | Unique name for this client device |
| `LOSEME_API_KEY` | Must match server key if auth is enabled |

---

## CLI Usage

The CLI runs inside the client container (or locally with `poetry run python -m client.cli.main`).

### Indexing

**Add a source and index a local directory:**
```bash
python -m client.cli.main sources add filesystem /path/to/documents
python -m client.cli.main sources scan <source-id>
```

**Index directly (one-shot, no persistent source):**
```bash
python -m client.cli.main ingest filesystem /path/to/documents
python -m client.cli.main ingest filesystem /path/to/docs --recursive --include-pattern "*.md" --include-pattern "*.txt"
python -m client.cli.main ingest filesystem /path/to/docs --exclude-pattern "*.log" --exclude-pattern "tmp/*"
```

**Index a Thunderbird mailbox:**
```bash
python -m client.cli.main ingest thunderbird /path/to/Inbox
python -m client.cli.main ingest thunderbird /path/to/Inbox --ignore-from "*@spam.com"
```

### Search

```bash
python -m client.cli.main search "machine learning gradient descent"
python -m client.cli.main search "project meeting notes" --top-k 20
python -m client.cli.main search "invoice from acme" --interactive   # opens selected file
```

### Source Management

```bash
# List all monitored sources
python -m client.cli.main sources list

# Add sources
python -m client.cli.main sources add filesystem /data/documents
python -m client.cli.main sources add thunderbird /data/mail/Inbox

# Rescan all sources
python -m client.cli.main sources scan-all

# Scan a specific source
python -m client.cli.main sources scan <source-id>
```

---

## Web UI

Open `http://localhost:3000` in your browser.

### Dashboard Tab

Overview of indexed content: total document parts, chunks, source instances, and devices. Lists all monitored sources in a collapsible tree grouped by path prefix.

Each source card shows:
- Source type (filesystem / thunderbird)
- File path / locator
- Document count
- Last ingested timestamp
- **Scan** button (triggers re-indexing from the browser)
- **Delete** button (removes source and all its vectors)

### Search Tab

Three-column layout:

| Column | Contents |
|--------|----------|
| **Left** | Ranked result cards with relevance score bars. Click to open the document. |
| **Centre** | Document viewer. Renders plaintext, markdown, PDFs, and emails inline. Highlights the matching chunk. |
| **Right** | LLM-synthesised answer streamed from a local Ollama instance, with source citations. |

The search bar at the bottom supports configurable `Top K`. The model selector populates from your local Ollama instance automatically.

**Supported file previews:** `.txt`, `.md`, `.rst`, `.py`, `.js`, `.ts`, `.css`, `.html`, `.pdf`, `.eml`, Thunderbird emails.

### Runs Tab

Full visibility into indexing run history. Filter by status or source type, group by either. Each run card shows:
- Run ID and status (with live pulse animation for running jobs)
- Discovered vs indexed document count with progress bar
- Stop / Resume / Delete actions

### Storage Tab

Chunk-level statistics: total document parts, total chunks, chunker version breakdown, and histograms of chunk size distribution and chunks-per-document distribution. Filterable by chunker.

---

## Embedding Models

Configure via `LOSEME_EMBEDDING_MODEL` in `.env.server`.

| Value | Model | Notes |
|-------|-------|-------|
| `sentence-transformer:all-MiniLM-L6-v2` | MiniLM | Default, fast, CPU-friendly |
| `sentence-transformer:all-mpnet-base-v2` | MPNet | Better quality, slower |
| `nomic-ai/nomic-embed-text-v1` | Nomic | Good quality, requires `trust_remote_code` |
| `bge-m3` | BGE-M3 | Best quality, hybrid search (dense + sparse + ColBERT), GPU recommended |

BGE-M3 requires `LOSEME_VECTOR_STORAGE=qdrant-hybrid`.

---

## Chunking Strategies

Configure via `LOSEME_CHUNKER` in `.env.server`.

| Value | Class | Description |
|-------|-------|-------------|
| `simple` | `SimpleTextChunker` | Fixed-size sliding window with overlap. Fast, no ML dependency. |
| `sentence` | `SentenceAwareChunker` | Splits on sentence boundaries. Never cuts mid-sentence. |
| `semantic` | `SemanticChunker` | Merges adjacent paragraphs by embedding similarity. Best quality, slowest. |

---

## Migrations

Both SQLite (metadata) and Qdrant (vector payloads) have a migration system that runs automatically on startup.

- **SQLite migrations:** `server/storage/metadata_db/migrations/` — numbered `.sql` or `.py` files.
- **Vector migrations:** `server/storage/vector_db/migrations/` — numbered `.py` files that receive `(conn, qdrant_client, collection_name)`.

Completed migrations are recorded in `schema_migrations` and `vector_migrations` tables and never re-run.

---

## API Authentication

Set `LOSEME_API_KEY` on the server. All requests must include:

```
X-API-Key: <your-key>
```

Exempt paths (no key required): `/health`, `/docs`, `/openapi.json`.

---

## Testing

The test suite runs without a live Qdrant instance. An `InMemoryVectorStore` and `DummyEmbeddingProvider` are injected automatically.

```bash
poetry run pytest
```

| File | Coverage |
|------|----------|
| `test_id_stability.py` | ID determinism — foundation of deduplication |
| `test_ingest_skip_logic.py` | Skip unchanged docs; reprocess on change |
| `test_chunker_contracts.py` | `SimpleTextChunker` and `SemanticChunker` invariants |
| `test_search_round_trip.py` | Full slice: ingest → vector store → search API |
| `test_run_lifecycle.py` | Indexing run state machine transitions |

---

## Maintenance Scripts

Run these inside the server container (`docker compose exec server python -m scripts.<name>`):

| Script | Purpose |
|--------|---------|
| `scripts/inspect_chunks.py` | Print chunk size stats and generate distribution plots |
| `api/app/audit_orphan_chunks.py` | Find and optionally delete Qdrant points with no matching SQLite record |
| `api/app/repair_chunker_migration.py` | Fix rows where chunker metadata is stale after a mid-run upgrade |

---

## License

Licensed under the [GNU AGPLv3](https://www.gnu.org/licenses/agpl-3.0.en.html).
