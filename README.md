# Semantic Memory

**Local-first semantic search over personal data**

## What is this?

Semantic Memory is a privacy-preserving system that lets you search your personal files by *meaning*, not just filenames or keywords. It runs entirely on your own devices—no cloud, no data leaks.

Think of it as a personal knowledge base that understands what your documents are about, making everything you've ever written instantly searchable by concept.

## Current Status: Phase 1 (MVP)

This implementation includes:

- **Filesystem ingestion**: Index text files (`.txt`, `.md`, `.rst`)
- **Local embeddings**: Deterministic vector generation (no external APIs)
- **Persistent vector database**: Qdrant-based semantic search
- **Resumable indexing**: Smart checkpointing to handle interruptions
- **REST API**: FastAPI server for ingestion and search
- **CLI client**: Simple command-line interface

## Architecture

The system follows a modular pipeline:

```
Filesystem → Extraction → Chunking → Embedding → Vector DB → Search
```

### Key Design Decisions

1. **Local-first**: All processing happens on your machine. No data leaves your network.

2. **Multi-device aware**: The system tracks which device indexed which files, enabling future cross-device search without syncing entire files—only metadata and embeddings are shared.

3. **Content-based identity**: Documents are identified by their content hash, not file path. This means the same document on different devices or paths is recognized as identical.

4. **Resumable processing**: Indexing runs can be interrupted and resumed without reprocessing documents.

5. **Dockerized**: Everything runs in containers for reproducibility and easy deployment.

## Quick Start

```bash
# Start all services
docker-compose up -d

# Ingest a directory
docker-compose run cli ingest /data/my-documents

# Search semantically
docker-compose run cli search "machine learning concepts" --top-k 5
```

## How It Works

1. **Ingestion**: Files are discovered, filtered, and their text extracted
2. **Chunking**: Documents are split into semantic chunks (500 chars with 50 char overlap)
3. **Embedding**: Each chunk is converted to a 384-dimensional vector
4. **Storage**: Vectors are stored in Qdrant, metadata in SQLite
5. **Search**: Query text is embedded and similar chunks are retrieved via cosine similarity

## Project Structure

```
semantic-memory/
├── api/              # FastAPI server
├── collectors/       # Data source connectors (filesystem)
├── pipeline/         # Processing stages (chunking, embeddings)
├── storage/          # Vector DB and metadata DB
├── clients/          # CLI and future UI clients
└── tests/            # Comprehensive test suite
```

## Future Roadmap

- **Phase 2**: LLM-based enrichment (summaries, tags, entities)
- **Phase 3**: Multi-device synchronization
- **Phase 4**: Images and OCR
- **Phase 5**: Connectors for self-hosted services (Immich, Paperless-ng, etc.)
- **Phase 6**: Email ingestion and mobile apps

## Technology Stack

- **Python 3.11+**
- **FastAPI** for the API layer
- **Qdrant** for vector storage
- **SQLite** for metadata
- **Docker** for deployment

## Design Principles

- **Privacy over convenience**: Your data stays yours
- **Incremental progress**: Build working features step by step
- **Meaning over structure**: Semantic understanding, not rigid organization
- **Local-first always**: Cloud is optional, never required

## Contributing

This project prioritizes clean, understandable code. Each module is independent and testable. See `/project_plan/full.md` for detailed architecture documentation.

## License
This project is licensed under the AGPLv3 License. See the [gnu website](https://www.gnu.org/licenses/agpl-3.0.en.html) for details.
