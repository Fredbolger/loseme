# Semantic Memory

A **local-first, privacy-preserving semantic memory system** that ingests personal data (files, images, emails, etc.), understands it using embeddings and local LLMs, and makes it searchable across devices.

This document describes the **vision, architecture, tech stack, requirements, and phased roadmap** so the project can be developed collaboratively using Git and Docker.

---

## 1. Vision & Goals

### 1.1 What problem are we solving?

Personal data grows faster than our ability to organize or remember it. Traditional folder structures and keyword search break down over time.

This project builds a **personal semantic memory** that:

* Understands *meaning*, not just filenames
* Works **fully locally** (no cloud, no data leaks)
* Scales across **multiple personal devices**
* Allows semantic search even when files are not present locally

### 1.2 Core goals

* Local-first, privacy-preserving
* Semantic search over heterogeneous data
* Modular, extensible architecture
* Beginner-friendly codebase
* Dockerized for reproducibility
* Multi-device aware

### 1.3 Non-goals (important)

* No cloud-based LLMs or embeddings
* No real-time collaboration features
* No full document synchronization by default

---

## 2. High-level Architecture

The system is composed of **four main layers**:

```
Collectors → Understanding Pipeline → Memory Core → Clients
```

### 2.1 Collectors

Responsible for ingesting raw data from various sources and normalizing it into a common document format.

Examples:

* Filesystem (Markdown, TXT, PDF)
* Images
* Emails (later phase)

### 2.2 Understanding Pipeline

Transforms raw documents into *meaning*:

* Text normalization
* Chunking
* Embedding generation
* LLM-based enrichment (tags, summaries, entities)

Each step is independent and optional.

### 2.3 Memory Core

The central "brain" of the system:

* Vector database (semantic meaning)
* Metadata database (structure, filters, device info)
* API for ingestion and search

This component can be hosted on a desktop PC or Raspberry Pi and accessed by other devices.

### 2.4 Clients

Ways to interact with the memory:

* CLI (initial)
* Web UI (later)
* Mobile app (future)

Clients **never talk directly to storage** — only to the API.

---

## 3. Multi-device Model

### 3.1 Key principle

> Only **metadata and embeddings** are shared across devices — not raw files.

### 3.2 Why this matters

* Files do not need to exist everywhere
* Storage remains lightweight
* Privacy is preserved
* Mobile devices can still search

### 3.3 Example

* Desktop PC ingests a PDF
* Laptop queries the semantic memory
* Result indicates:

  * Document summary
  * Tags
  * Source device
  * File path

Fetching the actual file is optional and explicit.

---

## 4. Tech Stack (Frozen)

### 4.1 Programming Language

* **Python 3.11+**

Chosen for its ML ecosystem, readability, and community support.

---

### 4.2 API Layer

* **FastAPI**

Responsibilities:

* Ingest documents
* Trigger processing pipeline
* Query vector database
* Filter by metadata
* Identify devices

Benefits:

* Automatic OpenAPI docs
* Async-ready
* Clean modular structure

---

### 4.3 Vector Database

* **Qdrant** (Dockerized)

Reasons:

* Fully local
* Fast similarity search
* Strong metadata filtering
* Production-grade

---

### 4.4 Metadata Database

* **SQLite** (Phase 1–2)
* **PostgreSQL** (Phase 3+)

Stores:

* Document metadata
* Device info
* File paths
* Tags, summaries
* Timestamps

---

### 4.5 Embedding Models

* **SentenceTransformers**

Initial models:

* `all-MiniLM-L6-v2`
* `bge-small-en-v1.5`

Characteristics:

* CPU-friendly
* Stable
* Well-documented

---

### 4.6 Local LLM

* **Ollama**

Used for:

* Tag generation
* Summaries
* Entity extraction

Initial models:

* `mistral:7b`
* `llama3.1:8b`
* `phi-3`

LLMs are **not** used for embeddings.

---

### 4.7 Image Understanding

* **CLIP** (via SentenceTransformers)
* **Tesseract OCR** (later)

Allows:

* Image ↔ text semantic search
* OCR-based text extraction

---

### 4.8 Parsing Libraries

* Filesystem: `pathlib`
* PDFs: `PyMuPDF` / `pdfplumber`
* Word: `python-docx`
* Markdown: `markdown`
* Email (later): `imaplib`, `mailbox`

---

### 4.9 Infrastructure

* **Docker**
* **Docker Compose**

Services:

```
api
qdrant
metadata-db
ollama
```

---

## 5. Repository Structure

```
semantic-memory/
├── docker-compose.yml
├── README.md
├── docs/
│   └── architecture.md
│
├── api/
│   ├── Dockerfile
│   ├── main.py
│   ├── routes/
│   └── schemas/
│
├── collectors/
│   ├── filesystem/
│   ├── images/
│   └── email/
│
├── pipeline/
│   ├── chunking/
│   ├── embeddings/
│   ├── llm_enrichment/
│   └── ocr/
│
├── storage/
│   ├── vector_db/
│   └── metadata_db/
│
├── clients/
│   └── cli/
│
└── models/
    └── local_llm/
```

---

## 6. Document Model (Canonical)

All ingested content is normalized into this structure:

```json
{
  "id": "uuid",
  "checksum": "....",
  "source": "filesystem",
  "device": "desktop-pc",
  "path": "/docs/report.md",
  "type": "text",
  "content": "...",
  "tags": ["finance", "project"],
  "summary": "Short description...",
  "entities": ["Alice", "Company X"],
  "geolocation": "...",
  "created_at": "...",
  "modified_at": "..."
}
```

---

## 7. Development Phases

### Phase 1 — MVP (Foundation)

**Goal:** End-to-end semantic search over local text files

Includes:

* Filesystem collector
* Text chunking
* Embedding generation
* Vector storage
* Search API
* CLI client

Excludes:

* Images
* LLM enrichment
* Multi-device sync
* Email

---

### Phase 2 — Semantic Enrichment

**Goal:** Improve search quality and understanding

Adds:

* Local LLM summaries
* Tag generation
* Entity extraction
* Metadata-based filtering

---

### Phase 3 — Multi-device Memory

**Goal:** Shared semantic memory across devices

Adds:

* Device IDs
* Remote API access
* Shared vector DB
* Optional file fetching

---

### Phase 4 — Images & OCR

**Goal:** Non-text data understanding

Adds:

* Image embeddings
* OCR text extraction
* Image ↔ text search

---

### Phase 5 — Email & Mobile

**Goal:** Complete personal knowledge base

Adds:

* Email ingestion
* Thread-level understanding
* Android client

---

## 8. Contribution Guidelines (Draft)

* One module per PR
* Clear commit messages
* No breaking API changes without discussion
* Prefer simple, readable code

---

## 9. Guiding Principles

* Privacy over convenience
* Incremental progress over perfection
* Meaning over structure
* Local-first always

---

## 10. Status

This document defines the **agreed baseline** for the project.

Any major changes to architecture or stack must be discussed and documented.

