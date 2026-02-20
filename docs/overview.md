# Project Architecture Overview

This document explains **what this project is**, **how it is structured**, and **how it is intended to be used**, in simple terms. It is written for developers who want to understand the idea without digging through the code first.

---

## 1. What is this project?

This project is a **local-first indexing and search backend**.

In short:

> It takes data from your local systems (files, documents, photos, services), breaks it into pieces, turns those pieces into vectors, and stores them so they can be searched semantically.

Key goals:

* Index **only selected directories or sources** (never the whole disk by accident)
* Support **multiple data sources** (filesystem now, Paperless / Immich later)
* Allow **stoppable and resumable indexing**
* Run as a **backend service** (API + workers)
* Be usable by different clients (CLI, web UI, other apps)

This is not just a script — it is designed as a **reusable service**.

---

## 2. High-level architecture

The system is built as a **pipeline** with clear stages:

```
Source (filesystem, services)
        ↓
Document (metadata)
        ↓
Chunking (split content)
        ↓
Embedding (vectors)
        ↓
Vector Store (search)
```

Each stage is isolated so it can be replaced or extended later.

---

## 3. Folder structure (top-level)

```
.
├── api
├── collectors
├── pipeline
├── storage
├── src
├── scripts
├── clients
├── docs
```

Below is what each folder does.

---

## 4. `collectors/` — Data ingestion sources

**Purpose:**

> Pull data from different sources and turn them into `Document` objects.

Current state:

```
collectors/
└── filesystem/
    └── filesystem_source.py
```

### Filesystem collector

* Walks selected directories
* Applies include / exclude patterns
* Produces stable document IDs
* Computes checksums

Example:

* Index `~/docs/*.md`
* Skip everything else

Later additions:

* Paperless (documents)
* Immich (photos, metadata, people, locations)
* Other local services

Each new source lives in its **own subfolder**.

---

## 5. `pipeline/` — Processing steps

**Purpose:**

> Transform documents into searchable vectors.

### 5.1 Chunking

```
pipeline/chunking/
└── simple_chunker.py
```

* Splits text into overlapping chunks
* Produces deterministic chunk IDs
* Keeps offsets and ordering

Example:

> A 3,000-character document becomes 6–10 chunks

Later:

* Different chunking strategies
* Media-aware chunking

---

### 5.2 Embeddings

```
pipeline/embeddings/
└── dummy.py
```

* Converts text into numeric vectors
* Current implementation is **dummy but deterministic**
* No ML dependencies yet

Purpose right now:

* Validate architecture
* Enable end-to-end testing

Later:

* Local embedding models
* Remote APIs
* GPU-backed embeddings

---

## 6. `storage/` — Persistence layers

**Purpose:**

> Store indexing metadata and vectors.

```
storage/
├── metadata_db
└── vector_db
    └── in_memory.py
```

### Vector DB

* In-memory vector store (Phase 1)
* Cosine similarity search

Later:

* Qdrant
* FAISS
* Other vector databases

### Metadata DB (planned)

* Indexing runs
* Progress tracking
* Resume state

---

## 7. `src/domain/` — Core domain models

**Purpose:**

> Define the *language* of the system.

```
src/domain/
├── models.py
├── ingestion.py
├── embeddings.py
└── vector_store.py
```

These files contain:

* `Document`
* `Chunk`
* `IndexingScope`
* `IndexingRun`

This layer:

* Has no infrastructure code
* Is reusable everywhere
* Keeps the system consistent

Think of this as the **contract** all parts agree on.

---

## 8. `scripts/` — Executable workflows

**Purpose:**

> Glue code that runs the pipeline.

```
scripts/
└── run_indexing.py
```

### `run_indexing.py`

This script:

1. Defines what to index
2. Runs ingestion
3. Chunks documents
4. Embeds chunks
5. Stores vectors
6. Runs a test query

This is the **reference implementation** of the pipeline.

Later scripts:

* Background workers
* Scheduled indexing
* Re-index specific scopes

---

## 9. `api/` — Backend service

**Purpose:**

> Expose the system via HTTP.

```
api/
└── app/
    ├── main.py
    ├── routes/
    └── schemas/
```

The API will:

* Start indexing runs
* Query indexed data
* Report progress
* Control stop / resume

Important:

> The API **does not contain business logic**.
> It only calls into the pipeline and storage layers.

---

## 10. How this project will be used later

### Typical workflow

1. User selects directories or sources
2. Backend starts an indexing run
3. Worker processes data incrementally
4. Progress is stored persistently
5. User can stop and resume safely
6. Clients query the vector store

### Clients

* CLI (`clients/cli`)
* Web UI
* Desktop apps (Electron)
* Other services

All clients talk to the **same backend**.

---

## 11. Design principles (important)

* Local-first
* Pull-based ingestion
* Deterministic processing
* Restartable by default
* Clear module boundaries
* Replaceable infrastructure

This is why the project is structured the way it is.

---

## 12. Current status

✔ Architecture validated end-to-end
✔ Runs inside Docker
✔ Deterministic indexing
✔ Ready for resumable indexing

Next step:

> **Persist and resume indexing runs**

---

This document should give new contributors a clear mental model of the system and where to start reading the code.

