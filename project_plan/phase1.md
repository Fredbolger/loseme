# Semantic Memory – Phase 1 Detailed Plan

This document breaks **Phase 1 (MVP / Foundation)** into **clear work packages and concrete tasks**. It is written so tasks can be distributed among contributors and tracked via Git issues or a project board.

Phase 1 is intentionally limited. The goal is **one complete vertical slice**: from local files → embeddings → vector search → usable results.

---

## Phase 1 Goal (Definition of Done)

By the end of Phase 1, the system must:

* Ingest local **text-based files** (Markdown, TXT, PDF)
* Chunk their content meaningfully
* Generate embeddings locally (CPU)
* Store embeddings in a vector database
* Expose a **search API**
* Provide a **CLI client** for ingestion and search
* Run fully via **Docker Compose**

Out of scope for Phase 1:

* Images
* OCR
* Local LLM summaries / tags
* Multi-device sync
* Email ingestion

If something is not required for the above goals, it does not belong in Phase 1.

---

## Phase 1 Architecture (Concrete)

```
Filesystem → Collector → Chunker → Embedder → Vector DB
                                    ↓
                                 Metadata DB

CLI → API → Vector DB + Metadata DB
```

---

## Work Package Overview

Phase 1 is divided into the following work packages:

1. Repository & Infrastructure Setup
2. Core Data Model
3. Filesystem Collector
4. Chunking Module
5. Embedding Module
6. Storage Layer
7. API Layer
8. CLI Client
9. Integration & Validation

Each package can be worked on mostly independently.

---

## 1. Repository & Infrastructure Setup

### Goal

Create a reproducible development environment that works the same on all machines.

### Tasks

* [ ] Create Git repository
* [ ] Add top-level README.md (project overview + Phase 1 scope)
* [x] Create base folder structure
* [x] Add `.gitignore`
* [x] Create `docker-compose.yml`
* [ ] Add API Dockerfile
* [ ] Add Qdrant service
* [ ] Add SQLite volume
* [ ] Verify `docker-compose up` works

### Acceptance Criteria

* One command (`docker-compose up`) starts all services
* API container responds to a health check
* Qdrant is reachable from API container

---

## 2. Core Data Model

### Goal

Define the **canonical internal representation** for documents and chunks.

### Tasks

* [ ] Define `Document` schema
* [ ] Define `Chunk` schema
* [ ] Define metadata fields (source, path, timestamps)
* [ ] Define device identifier strategy (static string for Phase 1)
* [ ] Add Pydantic models

### Acceptance Criteria

* Schemas are versioned and documented
* All downstream modules consume these schemas

---

## 3. Filesystem Collector

### Goal

Load text-based files from disk and convert them into normalized documents.

### Tasks

* [ ] Walk directory tree
* [ ] Filter supported file types (`.md`, `.txt`, `.pdf`)
* [ ] Extract raw text
* [ ] Capture metadata (path, modified time)
* [ ] Assign document IDs
* [ ] Return standardized `Document` objects

### Notes

* PDF parsing can be imperfect — that is acceptable in Phase 1
* Errors must not crash ingestion

### Acceptance Criteria

* Given a folder, documents are extracted without crashing
* Text content is non-empty for supported formats

---

## 4. Chunking Module

### Goal

Split documents into semantically meaningful chunks suitable for embeddings.

### Tasks

* [ ] Define chunk size (initially 500–700 tokens)
* [ ] Implement paragraph-based splitting
* [ ] Add overlap (10–20%)
* [ ] Assign chunk IDs
* [ ] Preserve document references

### Acceptance Criteria

* Chunks are neither too small nor too large
* Chunks retain document context

---

## 5. Embedding Module

### Goal

Generate vector embeddings locally for each chunk.

### Tasks

* [ ] Integrate SentenceTransformers
* [ ] Load `all-MiniLM-L6-v2`
* [ ] Batch embedding generation
* [ ] Normalize vectors if needed
* [ ] Handle empty or invalid chunks

### Acceptance Criteria

* Embeddings are generated deterministically
* Batch processing works
* No GPU required

---

## 6. Storage Layer

### Goal

Persist embeddings and metadata reliably.

### 6.1 Vector Database (Qdrant)

#### Tasks

* [ ] Create Qdrant collection
* [ ] Define vector size
* [ ] Store chunk embeddings
* [ ] Attach metadata payload

#### Acceptance Criteria

* Vector search returns expected chunks

---

### 6.2 Metadata Database (SQLite)

#### Tasks

* [ ] Define tables for documents and chunks
* [ ] Store file paths and timestamps
* [ ] Store source and device info
* [ ] Implement basic queries

#### Acceptance Criteria

* Metadata is queryable independently of vector DB

---

## 7. API Layer

### Goal

Expose ingestion and search functionality via HTTP.

### Required Endpoints

* `POST /ingest/filesystem`
* `POST /search`
* `GET /health`

### Tasks

* [ ] Setup FastAPI app
* [ ] Add Pydantic request/response models
* [ ] Wire ingestion pipeline
* [ ] Implement vector search
* [ ] Add basic metadata filtering
* [ ] Return ranked results

### Acceptance Criteria

* API is self-documented (Swagger)
* Search returns relevant results

---

## 8. CLI Client

### Goal

Provide a simple user interface for Phase 1.

### Tasks

* [ ] Create CLI using Typer
* [ ] Add `ingest` command
* [ ] Add `search` command
* [ ] Display results clearly
* [ ] Handle API connection errors

### Acceptance Criteria

* User can ingest a folder via CLI
* User can search semantically via CLI

---

## 9. Integration & Validation

### Goal

Ensure the full system works end-to-end.

### Tasks

* [ ] End-to-end ingestion test
* [ ] End-to-end search test
* [ ] Manual relevance testing
* [ ] Fix obvious failure modes
* [ ] Document known limitations

### Acceptance Criteria

* Fresh clone + Docker works
* Ingest → search loop succeeds

---

## Suggested Task Distribution

* **Infra / Docker**: 1 person
* **Collector + Chunking**: 1 person
* **Embeddings + Storage**: 1 person
* **API + CLI**: 1–2 people

---

## Phase 1 Exit Criteria

Phase 1 is complete when:

* System is usable daily for text search
* Contributors understand the codebase
* Architecture supports Phase 2 without refactoring

---

## What Comes Next

Phase 2 will introduce:

* Local LLM summaries
* Tag extraction
* Better filtering
* Quality improvements

But **none of that is allowed until Phase 1 is stable**.

