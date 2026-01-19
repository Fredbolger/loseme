Phase 1 – Semantic Memory
=========================

This document breaks **Phase 1 (MVP / Foundation)** into **work packages and concrete tasks**.
It is written so tasks can be distributed among contributors and tracked via Git issues or a project board.

Phase 1 is intentionally limited: the goal is **one complete vertical slice** from local files → embeddings → vector search → usable results.

Phase 1 Goal (Definition of Done)
---------------------------------

By the end of Phase 1, the system must:

* Ingest local **text-based files** (Markdown, TXT, PDF)
* Chunk their content (for now just trivial)
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

Phase 1 Architecture (Concrete)
-------------------------------

.. code-block:: text

   Filesystem → Collector → DocumentExtractos → Chunker → Embedder → Vector DB
                                                             ↓
                                                         Metadata DB

   CLI → API → Vector DB + Metadata DB

Repository & Infrastructure Setup
---------------------------------

**Goal:** Create a reproducible development environment that works the same on all machines.

**Tasks:**

* [x] Create Git repository
* [x] Add top-level README.md
* [x] Create base folder structure
* [x] Add `.gitignore`
* [x] Create `docker-compose.yml`
* [x] Add API Dockerfile
* [x] Add Qdrant service
* [x] Add SQLite volume
* [x] Verify `docker-compose up` works

**Acceptance Criteria:**

* One command (`docker-compose up`) starts all services
* API container responds to a health check
* Qdrant is reachable from API container

Core Data Model
---------------

**Goal:** Define the canonical internal representation for documents and chunks.

**Tasks:**

* [x] Define `Document` schema
* [x] Define `Chunk` schema
* [x] Define metadata fields (source, path, timestamps)
* [x] Define device identifier strategy
* [x] Add Pydantic models

**Acceptance Criteria:**

* Schemas are versioned and documented
* All downstream modules consume these schemas

Filesystem Collector
--------------------

**Goal:** Load text-based files from disk and convert them into normalized documents.

**Tasks:**

* [x] Walk directory tree
* [ ] Filter supported file types (`.md`, `.txt`, `.pdf`)
* [x] Extract raw text
* [x] Capture metadata (path, modified time)
* [x] Assign document IDs
* [x] Return standardized `Document` objects

**Notes:**

* Errors must not crash ingestion

**Acceptance Criteria:**

* Documents are extracted without crashing
* Text content is non-empty for supported formats

Chunking Module
---------------

**Goal:** Split documents into semantically meaningful chunks suitable for embeddings.
This is currently delayed into Phase 2. 

**Tasks:**

* [ ] Define chunk size (500–700 tokens)
* [ ] Implement paragraph-based splitting
* [ ] Add overlap (10–20%)
* [x] Assign chunk IDs
* [ ] Preserve document references

**Acceptance Criteria:**

* Chunks are neither too small nor too large
* Chunks retain document context

Embedding Module
----------------

**Goal:** Generate vector embeddings locally for each chunk.

**Tasks:**

* [ ] Integrate SentenceTransformers
* [ ] Load `all-MiniLM-L6-v2`
* [ ] Batch embedding generation
* [ ] Normalize vectors if needed
* [ ] Handle empty or invalid chunks

**Acceptance Criteria:**

* Embeddings are generated deterministically
* Batch processing works
* No GPU required

Storage Layer
-------------

### Vector Database (Qdrant)

**Tasks:**

* [x] Create Qdrant collection
* [x] Define vector size
* [x] Store chunk embeddings
* [x] Attach metadata payload

**Acceptance Criteria:**

* Vector search returns expected chunks

### Metadata Database (SQLite)

**Tasks:**

* [x] Define tables for documents and chunks
* [x] Store file paths and timestamps
* [x] Store source and device info
* [x] Implement basic queries

**Acceptance Criteria:**

* Metadata is queryable independently of vector DB

API Layer
---------

**Goal:** Expose ingestion and search functionality via HTTP.

**Required Endpoints:**

* `POST /ingest/filesystem`
* `POST /search`
* `GET /health`

**Tasks:**

* [x] Setup FastAPI app
* [x] Add Pydantic request/response models
* [x] Wire ingestion pipeline
* [x] Implement vector search
* [ ] Add basic metadata filtering
* [x] Return ranked results

**Acceptance Criteria:**

* API is self-documented (Swagger)
* Search returns relevant results

CLI Client
----------

**Goal:** Provide a simple user interface for Phase 1.

**Tasks:**

* [x] Create CLI using Typer
* [x] Add `ingest` command
* [x] Add `search` command
* [ ] Display results clearly
* [ ] Handle API connection errors

**Acceptance Criteria:**

* User can ingest a folder via CLI
* User can search semantically via CLI

Integration & Validation
------------------------

**Goal:** Ensure the full system works end-to-end.

**Tasks:**

* [ ] End-to-end ingestion test
* [ ] End-to-end search test
* [ ] Manual relevance testing
* [ ] Fix obvious failure modes
* [ ] Document known limitations

**Acceptance Criteria:**

* Fresh clone + Docker works
* Ingest → search loop succeeds

Suggested Task Distribution
---------------------------

* Infra / Docker: 1 person
* Collector + Chunking: 1 person
* Embeddings + Storage: 1 person
* API + CLI: 1–2 people

Phase 1 Exit Criteria
---------------------

Phase 1 is complete when:

* System is usable daily for text search
* Contributors understand the codebase
* Architecture supports Phase 2 without refactoring

What Comes Next
---------------

Phase 2 will introduce:

* Local LLM summaries
* Basic chunking
* Tag extraction
* Better filtering
* Quality improvements

But **none of that is allowed until Phase 1 is stable**.
