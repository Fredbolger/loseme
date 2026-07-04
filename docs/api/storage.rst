Storage
=======

The storage layer is split between metadata (SQLite) and vectors (Qdrant).

Metadata Database
-----------------

SQLite-based storage for indexing runs, document parts, and source metadata.

.. automodule:: server.storage.metadata_db.db
   :members:

.. automodule:: server.storage.metadata_db.models
   :members:

.. automodule:: server.storage.metadata_db.indexing_runs
   :members:

.. automodule:: server.storage.metadata_db.document_parts
   :members:

.. automodule:: server.storage.metadata_db.document_parts_queue
   :members:

.. automodule:: server.storage.metadata_db.search_sessions
   :members:

Vector Database
--------------

Vector storage for embeddings with metadata. Supports Qdrant and in-memory backends.

.. automodule:: server.storage.vector_db.vector_store
   :members:

.. automodule:: server.storage.vector_db.qdrant_store
   :members:

.. automodule:: server.storage.vector_db.qdrant_store_hybrid
   :members:

.. automodule:: server.storage.vector_db.in_memory
   :members:

.. automodule:: server.storage.vector_db.runtime
   :members:
