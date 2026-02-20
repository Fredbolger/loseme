# Local Semantic Memory

**Local-first semantic search over personal data**

## What is this?

Local Semantic Memory is a privacy-preserving system that lets you search your personal files by *meaning*, not just filenames or keywords. It runs entirely on your own devices.

Think of it as a personal knowledge base that understands what your documents are about, making everything you've ever written/mailed/developed easily searchable by content.

## Current Status: Phase 1

This implementation includes:

- **Filesystem ingestion**: Index plain text files (`.txt`, `.md`)
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

1. **Local-first**: All processing happens on your machine. Data should not leave your control.

2. **Multi-device aware**: The system tracks which device indexed which files, enabling future cross-device search without syncing entire files-only metadata and embeddings are shared.

3. **Content-based identity**: Documents are identified by their content hash, not file path. This means the same document on different devices or paths is recognized as identical.

4. **Resumable processing**: Indexing runs can be interrupted and resumed without reprocessing documents.

5. **Dockerized**: Everything runs in containers for reproducibility and easy deployment.

## Quick Start

```bash
# Start all services
docker-compose up -d

# Ingest a directory
python -m clients.cli.main ingest /data/my-documents

# Search semantically
docker-compose run cli search "machine learning concepts" --top-k 5
```

## How It Works

1. **Ingestion**: Files are discovered (based on currently implemented collectors), filtered, and their text extracted (based on the currently implemented extractors)
2. **Chunking**: Documents are split into semantic chunks (e.g., 500 tokens with 50 token overlap)
3. **Embedding**: Each chunk is converted to a vector using a local embedding model (e.g., Sentence Transformers)
4. **Storage**: Vectors are stored in Qdrant, metadata in SQLite
5. **Search**: Query text is embedded and similar chunks are retrieved via cosine similarity

## Project Structure

```
semantic-memory/

├── src/              # Main source code
├── api/              # FastAPI server
├── collectors/       # Data source connectors (filesystem)
├── pipeline/         # Processing stages (chunking, embeddings)
├── storage/          # Vector DB and metadata DB
├── scripts/          # Indexing and maintenance scripts
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

- **Privacy over convenience**: Private data should always stay private
- **Incremental progress**: Build working features step by step and enable easy improvements

## Contributing

This project prioritizes clean, understandable code. Each module is independent and testable. See `/project_plan/full.md` for detailed architecture documentation.

## License
This project is licensed under the AGPLv3 License. See the [gnu website](https://www.gnu.org/licenses/agpl-3.0.en.html) for details.
