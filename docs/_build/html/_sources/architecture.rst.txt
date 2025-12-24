Architecture
============

The Vector DB Project is structured as a set of loosely coupled components
that communicate through well-defined data structures and interfaces.

This architecture is designed to be:

- Easy to extend
- Easy to test
- Safe to evolve over time

The system follows a clear data flow from ingestion to storage, with each
layer having a single, well-defined responsibility.

--------------------------------------------------------------------------

High-Level Flow
---------------

At a high level, the system processes documents in the following steps:

1. Collectors ingest raw data from external sources
2. The pipeline processes and enriches documents
3. Storage persists metadata and vector representations
4. Domain models define the contracts between all components

Each stage can be extended or replaced independently.

--------------------------------------------------------------------------

Collectors
----------

Collectors are responsible for data ingestion.

They are the system's boundary to the outside world and handle the discovery
and reading of raw documents.

Typical responsibilities include:

- Discovering documents from a source
- Reading raw content
- Attaching source-specific metadata
- Emitting normalized document objects

Examples of collectors:

- Filesystem-based ingestion
- Future extensions such as Git repositories, web crawlers, or object storage

Code location::

    collectors/

--------------------------------------------------------------------------

Pipeline
--------

The pipeline transforms raw documents into searchable representations.

It is split into independent stages to allow experimentation and replacement
without impacting the rest of the system.

Chunking
~~~~~~~~

Chunking splits documents into smaller, semantically meaningful units.

Design goals:

- Preserve semantic coherence
- Control chunk size and overlap
- Improve embedding quality

Chunking is intentionally isolated so that multiple strategies can coexist.

Code location::

    pipeline/chunking/

Embedding
~~~~~~~~~

Embedding transforms text chunks into vector representations.

Design goals:

- Pluggable embedding backends
- Clear, stable interfaces
- No coupling to storage or ingestion logic

This makes it easy to switch between embedding models or providers.

Code location::

    pipeline/embeddings/

--------------------------------------------------------------------------

Storage
-------

Storage is explicitly split by responsibility to avoid tight coupling.

Metadata Database
~~~~~~~~~~~~~~~~~

The metadata database stores structured information about documents and runs.

Examples include:

- Document identifiers and checksums
- Processing status
- Indexing runs and timestamps

This layer is typically backed by a relational database such as SQLite.

Code location::

    storage/metadata_db/

Vector Store
~~~~~~~~~~~~

The vector store is responsible for storing and querying vector embeddings.

Design goals:

- Backend-agnostic interface
- Replaceable implementations
- No knowledge of document ingestion details

This separation enables experimentation with different vector databases.

Code location::

    storage/vector_db/

--------------------------------------------------------------------------

Domain Layer
------------

The domain layer defines the core abstractions shared across the system.

It acts as the architectural backbone and protects the rest of the codebase
from implementation churn.

Typical responsibilities include:

- Defining document and chunk models
- Declaring embedding and vector store interfaces
- Enforcing invariants and contracts

All higher-level components depend on the domain layer, not the other way around.

Code location::

    src/domain/

--------------------------------------------------------------------------

Design Principles
-----------------

The project follows a small set of explicit design principles:

- Explicit over implicit
- Interfaces before implementations
- Side effects pushed to the edges
- Docker-first execution model

These principles are intended to keep the system understandable as it grows.

--------------------------------------------------------------------------

Future Extensions
-----------------

The architecture is designed to support future extensions, including:

- Re-ranking and hybrid search
- Streaming or incremental ingestion
- Multiple vector store backends
- Distributed or parallel execution

