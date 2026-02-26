Vector DB Project
=================

A modular, extensible system for **document ingestion, processing, embedding, and retrieval**
designed to support semantic search and vector-based applications.

The project is built around a **pipeline architecture**:

- Ingest data from multiple sources (filesystem, APIs, future connectors)
- Normalize and chunk documents
- Generate vector embeddings
- Store metadata and vectors separately
- Enable efficient querying and re-ranking

This documentation covers both the **architecture** and the **Python API**.

---

Key Concepts
------------

**Ingestion**
  Collects raw documents from external sources and normalizes them into a common format.

**Pipeline**
  Processes documents through chunking and embedding stages.

**Storage**
  Separates concerns between metadata storage and vector storage.

**Domain Layer**
  Defines core interfaces and abstractions used across the system.

---

Getting Started
---------------

The system is designed to run inside Docker and can be extended incrementally.
Start with the architecture overview to understand how the pieces fit together.

---

Documentation
-------------

.. toctree::
   :maxdepth: 2
   :caption: Overview

   architecture
   phase1

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/pipeline
   api/storage
   api/domain

