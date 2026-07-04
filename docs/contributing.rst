Contributing
============

Thank you for your interest in contributing to LoseMe! This guide covers 
design principles, development practices, and how to extend the system.

--------------------------------------------------------------------------

Design Principles
----------------

LoseMe is built on a set of core principles that guide all development:

**Local-first**
  All processing (embedding, indexing, search) happens on your own hardware. 
  No data leaves your machine. No cloud API calls are made during core operations.

**Privacy-preserving**
  The system is designed to respect user privacy. Original documents remain 
  in their original locations and are only accessed for indexing when explicitly 
  requested by the user.

**Deterministic**
  Reproducible IDs are the foundation of the deduplication strategy. Given the 
  same inputs, the system always produces the same outputs. This ensures no duplicate 
  indexing and allows safe re-processing.

**Resumable**
  Indexing runs can be safely stopped and resumed. The system tracks progress 
  and skips already-processed documents on resume.

**Replaceable Components**
  Each major component (chunker, embedder, vector store, source) is behind a 
  clean interface. This allows experimentation and improvement without affecting 
  the rest of the system.

**Clear Boundaries**
  Layers have single, well-defined responsibilities. Client handles discovery and 
  extraction. Server handles processing, embedding, and storage. Core defines shared 
  contracts.

**Multi-device Awareness**
  The same file on different devices gets separate embeddings, tracked by device_id. 
  This prevents duplicates without requiring a shared filesystem.

--------------------------------------------------------------------------

Code Structure
--------------

::

    .
    ├── core/                      # Shared Python package
    │   └── loseme_core/           # Domain models, IDs, config
    │
    ├── server/                    # Server container
    │   ├── api/app/               # FastAPI application
    │   │   ├── routes/            # API endpoints
    │   │   └── core/              # Auth, middleware
    │   ├── pipeline/              # Processing pipeline
    │   │   ├── chunking/          # Chunking strategies
    │   │   └── embeddings/        # Embedding providers
    │   ├── storage/               # Persistence
    │   │   ├── metadata_db/       # SQLite storage
    │   │   └── vector_db/         # Vector storage
    │   ├── preview/               # Preview generators
    │   └── wiring.py              # Component factory
    │
    ├── client/                    # Client container
    │   ├── cli/                   # Typer CLI
    │   ├── extractors/            # File type extractors
    │   ├── sources/               # Document sources
    │   ├── ingest/                # Queue client
    │   ├── web/                   # Web frontend
    │   └── preview/               # Client preview
    │
    └── tests/                     # Test suite

**Core Package (``core/loseme_core/``)**
  Shared domain models and utilities. Installed as a dependency in both client 
  and server. Changes here require version bumps and reinstallation.

**Server (``server/``)**
  FastAPI application with all API endpoints, processing pipeline, storage, and 
  preview generation. Runs as a Docker container with optional GPU support.

**Client (``client/``)**
  CLI and web UI for document discovery, extraction, and user interaction. 
  Communicates with server via REST API.

**Tests (``tests/``)**
  Comprehensive test suite using pytest. Tests use in-memory vector store and 
  dummy embedding provider for fast, isolated testing.

--------------------------------------------------------------------------

Development Setup
----------------

**Prerequisites:**

- Python 3.11+
- Poetry (recommended) or pip
- Docker and Docker Compose (for full stack testing)

**Install dependencies:**

.. code-block:: bash

    # Clone the repository
    git clone <repository-url> loseme
    cd loseme
    
    # Install with Poetry (recommended)
    poetry install
    
    # Or with pip
    pip install -e .
    pip install -e ./core
    pip install -e ./server
    pip install -e ./client

**Environment setup:**

.. code-block:: bash

    # Copy example files
    cp .env.server.example .env.server
    cp .env.client.example .env.client
    
    # Edit as needed
    nano .env.server
    nano .env.client

**Start development services:**

.. code-block:: bash

    # Start Qdrant (in background)
    docker run -d -p 6333:6333 -v qdrant_data:/qdrant/storage qdrant/qdrant
    
    # Start server in development mode
    cd server
    uvicorn api.app.main:app --reload --host 0.0.0.0 --port 8000
    
    # In another terminal, start client
    cd client
    uvicorn web.main:app --reload --host 0.0.0.0 --port 3000

**Run tests:**

.. code-block:: bash

    pytest
    
    # With coverage
    pytest --cov=server --cov=client --cov=core
    
    # Specific test file
    pytest tests/test_ids.py

--------------------------------------------------------------------------

Code Style
----------

**Python:**

- Follow PEP 8 guidelines
- Use type hints for function signatures and variables
- Use Pydantic models for data validation
- Use logging instead of print statements
- Keep functions small and focused
- Add docstrings for public functions and classes

**Naming:**

- ``snake_case`` for variables and functions
- ``PascalCase`` for classes
- ``SCREAMING_SNAKE_CASE`` for constants
- ``_private`` prefix for internal-only attributes

**Imports:**

- Group imports: standard library, third-party, local
- Sort imports within groups alphabetically
- Use absolute imports within the project
- Import specific items rather than using ``*``

**Logging:**

- Use module-level logger: ``logger = logging.getLogger(__name__)``
- Use appropriate log levels: DEBUG, INFO, WARNING, ERROR
- Include context in log messages

--------------------------------------------------------------------------

Extending LoseMe
---------------

Adding a New Source Type
~~~~~~~~~~~~~~~~~~~~~~~~

To add support for a new document source (e.g., a new cloud service):

1. **Create scope model** in ``core/loseme_core/``:

.. code-block:: python

    # core/loseme_core/my_source_model.py
    from loseme_core.scope_models import IndexingScope
    
    class MySourceIndexingScope(IndexingScope):
        type: str = "my_source"
        # Add source-specific fields
        api_url: str
        credentials: dict
        
        def serialize(self) -> dict:
            return self.model_dump()

2. **Create ingestion source** in ``client/sources/``:

.. code-block:: python

    # client/sources/my_source/my_source_source.py
    from loseme_core.models import IngestionSource, DocumentPart, OpenDescriptor
    from loseme_core.my_source_model import MySourceIndexingScope
    
    class MySourceIngestionSource(IngestionSource):
        def __init__(self, scope: MySourceIndexingScope, should_stop, update_if_changed_after):
            super().__init__(scope, should_stop, update_if_changed_after)
            self.scope = scope
            
        def iter_documents(self) -> list:
            # Connect to your source and yield Document objects
            # Each Document should have parts that are DocumentPart objects
            pass
            
        def get_open_descriptor(self, document_id: str) -> OpenDescriptor:
            # Return how to open this document
            return OpenDescriptor(
                source_type="my_source",
                target=document_id,
                extra={"url": self.scope.api_url}
            )
            
        def extract_by_document_id(self, document_id: str) -> DocumentPart:
            # Fetch and return the full document
            pass

3. **Register in extractor_registry** in ``client/sources/my_source/__init__.py``:

.. code-block:: python

    from .my_source_source import MySourceIngestionSource
    from loseme_core.models import ingestion_source_registry
    
    ingestion_source_registry.register("my_source", MySourceIngestionSource)

4. **Add CLI commands** in ``client/cli/sources.py``:

.. code-block:: python

    @sources_app.command("my-source")
    def add_my_source(
        api_url: str = typer.Argument(...),
        # other params
    ):
        scope = MySourceIndexingScope(
            type="my_source",
            api_url=api_url,
            # ...
        )
        # Register with server
        with get_client() as client:
            r = client.post("/sources/add", json={"scope": scope.serialize()})
        
5. **Add to server wiring** if needed for server-side handling.

Adding a New Extractor
~~~~~~~~~~~~~~~~~~~~~

To add support for a new file type:

1. **Create extractor** in ``client/extractors/``:

.. code-block:: python

    # client/extractors/newfile_extractor.py
    from pathlib import Path
    from extractors.extractor import DocumentExtractor, DocumentExtractionResult
    
    class NewFileExtractor(DocumentExtractor):
        name = "newfile"
        version = "1.0"
        priority = 10
        supported_mime_types = {"application/x-newfile"}
        
        def can_extract(self, path: Path) -> bool:
            return path.suffix == ".newfile"
            
        def can_extract_bytes(self, file_bytes: bytes) -> bool:
            # Check magic bytes or content
            return file_bytes.startswith(b"NEWFILE")
            
        def extract(self, path: Path) -> DocumentExtractionResult:
            with open(path, "rb") as f:
                content = f.read()
            
            # Parse and extract text and metadata
            text = parse_newfile(content)
            metadata = {"custom_field": "value"}
            
            return DocumentExtractionResult(
                texts=[text],
                metadata=[metadata],
                unit_locators=[str(path)],
                content_types=["text/plain"],
                extractor_names=[self.name],
                extractor_versions=[self.version],
                is_multipart=False
            )

2. **Register in extractor_registry** in ``client/extractors/__init__.py``:

.. code-block:: python

    from .newfile_extractor import NewFileExtractor
    extractor_registry.register(NewFileExtractor())

Adding a New Chunker
~~~~~~~~~~~~~~~~~~~~

To add a new chunking strategy:

1. **Create chunker** in ``server/pipeline/chunking/``:

.. code-block:: python

    # server/pipeline/chunking/my_chunker.py
    from typing import List, Tuple
    from loseme_core.models import Chunk, DocumentPart
    from loseme_core.ids import make_chunk_id
    
    class MyChunker:
        name = "my_chunker"
        version = "1.0"
        
        def __init__(self, max_size: int = 1000):
            self.max_size = max_size
            
        def chunk(self, part: DocumentPart) -> Tuple[List[Chunk], List[str]]:
            # Implement your chunking logic
            chunks = []
            chunk_texts = []
            
            # Example: split by paragraphs
            paragraphs = part.text.split("\n\n")
            for i, para in enumerate(paragraphs):
                if not para.strip():
                    continue
                
                chunk_id = make_chunk_id(
                    document_part_id=part.document_part_id,
                    document_checksum=part.checksum,
                    index=i,
                )
                
                chunks.append(Chunk(
                    id=chunk_id,
                    document_part_id=part.document_part_id,
                    source_type=part.source_type,
                    source_path=part.source_path,
                    document_checksum=part.checksum,
                    device_id=part.device_id,
                    index=i,
                    unit_locator=part.unit_locator,
                    metadata={"char_len": len(para)},
                    text=para
                ))
                chunk_texts.append(para)
                
            return chunks, chunk_texts

2. **Add to wiring.py** in ``server/wiring.py``:

.. code-block:: python

    def build_chunker():
        # ... existing code ...
        
        elif CHUNKER_TYPE == "my_chunker":
            from pipeline.chunking.my_chunker import MyChunker
            return MyChunker()

3. **Set environment variable:**

.. code-block:: bash

    export LOSEME_CHUNKER=my_chunker

Adding a New Embedding Model
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To add support for a new embedding model:

1. **Create embedding provider** in ``server/pipeline/embeddings/``:

.. code-block:: python

    # server/pipeline/embeddings/my_embedder.py
    from typing import List
    from loseme_core.domain import EmbeddingOutput, EmbeddingProvider
    
    class MyEmbeddingProvider(EmbeddingProvider):
        name = "my_embedder"
        version = "1.0"
        
        def __init__(self, model_name: str = "my-model"):
            self.model_name = model_name
            # Load model here
            
        def dimension(self) -> int:
            return 384  # Your model's dimension
            
        def embed_query(self, text: str) -> EmbeddingOutput:
            # Generate embedding for query
            vector = self._generate_embedding(text)
            return EmbeddingOutput(dense=vector)
            
        def embed_document(self, text: str) -> EmbeddingOutput:
            # Generate embedding for document
            vector = self._generate_embedding(text)
            return EmbeddingOutput(dense=vector)
            
        def _generate_embedding(self, text: str) -> List[float]:
            # Your embedding generation logic
            pass

2. **Add to wiring.py** in ``server/wiring.py``:

.. code-block:: python

    def build_embedding_provider():
        # ... existing code ...
        
        elif EMBEDDING_MODEL == "my-model":
            from pipeline.embeddings.my_embedder import MyEmbeddingProvider
            return MyEmbeddingProvider()

3. **Set environment variable:**

.. code-block:: bash

    export LOSEME_EMBEDDING_MODEL=my-model

Adding a New Preview Generator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To add support for previewing a new document type:

1. **Create generator** in ``server/preview/generators/``:

.. code-block:: python

    # server/preview/generators/my_preview.py
    from preview.models import PreviewResult
    from preview.registry import PreviewGenerator
    
    class MyPreviewGenerator(PreviewGenerator):
        name = "my_preview"
        priority = 5
        
        def can_handle(self, source_type: str, doc_part: dict) -> bool:
            return doc_part.get("content_type") == "application/x-mytype"
            
        def generate(self, doc_part: dict) -> PreviewResult:
            # Generate HTML preview
            html = self._render_my_format(doc_part)
            return PreviewResult(
                content_type="text/html",
                content=html
            )

2. **Register in registry** in ``server/preview/generators/__init__.py``:

.. code-block:: python

    from .my_preview import MyPreviewGenerator
    preview_registry.register(MyPreviewGenerator())

--------------------------------------------------------------------------

Testing
-------

LoseMe includes a comprehensive test suite that can be extended:

**Test structure:**

- ``tests/test_ids.py`` - ID determinism tests
- ``tests/test_ingest_skip_logic.py`` - Skip logic tests
- ``tests/test_chunkers.py`` - Chunker tests
- ``tests/test_embeddings.py`` - Embedding tests
- ``tests/test_vector_store.py`` - Vector store tests
- ``tests/test_document_models.py`` - Document model tests
- ``tests/test_metadata_db.py`` - Metadata DB tests
- ``tests/test_search_sessions.py`` - Search session tests
- ``tests/test_extractors.py`` - Extractor tests
- ``tests/test_preview.py`` - Preview tests
- ``tests/test_api_integration.py`` - API integration tests

**Writing tests:**

Tests use the in-memory vector store and dummy embedding provider to avoid 
requiring external services:

.. code-block:: python

    from server.storage.vector_db.in_memory import InMemoryVectorStore
    from server.pipeline.embeddings.dummy import DummyEmbeddingProvider
    from loseme_core.models import DocumentPart, Chunk
    from loseme_core.ids import make_chunk_id
    
    def test_my_chunker():
        # Setup
        chunker = MyChunker()
        part = DocumentPart(
            document_part_id="test-part-1",
            text="This is a test document.\n\nSecond paragraph.",
            source_type="test",
            source_path="/test",
            checksum="abc123",
            device_id="test-device",
            unit_locator="test-locator",
            content_type="text/plain",
            extractor_name="test",
            extractor_version="1.0",
        )
        
        # Test
        chunks, texts = chunker.chunk(part)
        
        # Assert
        assert len(chunks) == 2
        assert all(isinstance(c, Chunk) for c in chunks)

**Running tests:**

.. code-block:: bash

    pytest
    pytest tests/test_chunkers.py
    pytest -v
    pytest --cov

--------------------------------------------------------------------------

Git Workflow
------------

**Branching:**

- ``main`` - Production-ready code (protected)
- ``develop`` - Integration branch for features
- ``feature/*`` - Individual feature branches
- ``fix/*`` - Bug fix branches
- ``docs/*`` - Documentation improvements

**Committing:**

- Use descriptive commit messages
- Follow Conventional Commits style (feat:, fix:, docs:, refactor:, etc.)
- Keep commits small and focused
- Include related test updates in the same commit

**Pull Requests:**

- Target ``develop`` branch for new features
- Target ``main`` for critical fixes (with approval)
- Include description of changes
- Link to related issues
- Ensure all tests pass
- Include screenshots for UI changes

**Code Review:**

- At least one approval required for merging
- Focus on code quality, not just functionality
- Check for security issues
- Verify documentation is updated
- Ensure tests are comprehensive

--------------------------------------------------------------------------

Reporting Issues
---------------

When reporting issues:

1. **Check existing issues** to avoid duplicates
2. **Include version information:**
   - LoseMe version
   - Python version
   - Docker version
   - OS information
3. **Describe the problem:**
   - What you were trying to do
   - What happened
   - What you expected to happen
4. **Include logs** if relevant
5. **Include steps to reproduce** if possible
6. **Include configuration** (with sensitive info redacted)

--------------------------------------------------------------------------

Security Considerations
----------------------

**API Authentication:**

- Always use API keys in production
- Rotate keys regularly
- Never commit keys to version control
- Use environment variables or secret management

**Data Protection:**

- All data stays local by design
- Ensure Docker volumes are backed up
- Consider encrypting sensitive documents before indexing
- Be aware that embeddings may contain information from the original text

**Dependencies:**

- Review third-party dependencies for security issues
- Keep dependencies updated
- Use pinned versions in production

--------------------------------------------------------------------------

Additional Resources
------------------

- **README.md**: Project overview and quick start
- **API Documentation**: http://localhost:8000/docs (when running)
- **Issue Tracker**: <link-to-issues>
- **Discussions**: <link-to-discussions>

For questions or support, please open an issue or discussion on the project repository.
