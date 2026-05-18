# LoseMe Test Suite

## Overview

| File | What it tests |
|------|--------------|
| `conftest.py` | Shared fixtures: in-memory SQLite, DummyEmbeddingProvider, InMemoryVectorStore |
| `test_ids.py` | ID determinism — foundation of deduplication |
| `test_chunkers.py` | SimpleTextChunker, SentenceAwareChunker, SemanticChunker contracts |
| `test_vector_store.py` | InMemoryVectorStore: add, search, remove, clear |
| `test_embeddings.py` | DummyEmbeddingProvider, EmbeddingOutput model, round-trip |
| `test_extractors.py` | PlainText, HTML, Python, PDF, EML extractors + ExtractorRegistry |
| `test_metadata_db.py` | SQLite schema: runs, document_parts, queue, monitored_sources |
| `test_document_models.py` | DocumentPart, Document, Chunk Pydantic validation |
| `test_scope_models.py` | FilesystemScope, ThunderbirdScope: serialize/deserialize/locator |
| `test_preview.py` | PreviewRegistry, server+client Plaintext/EML generators |
| `test_docker_path_translation.py` | host↔container path translation, round-trip |
| `test_cache.py` | TTLCache: set/get, expiry, invalidate, prefix invalidation |
| `test_api_integration.py` | All FastAPI routes via TestClient (no Qdrant, no GPU) |
| `test_ingest_skip_logic.py` | Skip-on-reingest, reprocess on change, force_reprocess |

## Running locally

```bash
# From repo root
PYTHONPATH=server:client:core pytest tests/ -v
```

## Running on Raspberry Pi / Drone CI

The pipeline in `.drone.yml` installs only CPU-safe dependencies.
No GPU, no Qdrant, no `torch` required.

```bash
# Unit tests only (fastest)
PYTHONPATH=server:client:core pytest tests/ -m "not integration" -v

# Integration tests (uses FastAPI TestClient + in-memory store)
PYTHONPATH=server:client:core pytest tests/test_api_integration.py tests/test_ingest_skip_logic.py -v

# With coverage
PYTHONPATH=server:client:core pytest tests/ --cov=server --cov=client --cov=core --cov-report=term-missing
```

## Design decisions

- **No Qdrant** — `InMemoryVectorStore` is injected everywhere via `monkeypatch` / `patch`.
- **No GPU / ML models** — `DummyEmbeddingProvider` produces deterministic hash-based embeddings.
- **No disk DB** — all metadata tests use an `:memory:` SQLite connection from `db_conn` fixture.
- **Module-scoped clients** — `app_client` is `scope="module"` in integration tests to amortise app initialisation cost on slow hardware.
- **Isolated test state** — each test that needs a run ID creates a fresh one; no shared mutable state between tests.
