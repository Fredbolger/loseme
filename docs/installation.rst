Installation
============

This guide covers setting up LoseMe for development or production use.

--------------------------------------------------------------------------

Prerequisites
-------------

**Required:**

- Docker 20.10+
- Docker Compose 2.0+
- Python 3.11+ (for local development without Docker)

**Recommended:**

- NVIDIA GPU with CUDA drivers (for fast embedding generation)
- 8GB+ RAM (for embedding models)
- 50GB+ disk space (for model caches and vector data)

--------------------------------------------------------------------------

Quick Start with Docker Compose
-------------------------------

The easiest way to run LoseMe is using Docker Compose.

**Step 1: Clone and configure**

.. code-block:: bash

    git clone <repository-url> loseme
    cd loseme
    
    # Create environment files from examples
    cp .env.server.example .env.server
    cp .env.client.example .env.client

**Step 2: Edit configuration**

Edit ``.env.server`` and set at minimum:

.. code-block:: bash

    LOSEME_DEVICE_ID=my-server
    # Optionally set API key for authentication
    # LOSEME_API_KEY=your-secret-key

Edit ``.env.client`` and set:

.. code-block:: bash

    LOSEME_API_URL=http://server:8000
    LOSEME_HOST_ROOT=/path/to/your/files
    LOSEME_CONTAINER_ROOT=/mnt/userdata
    LOSEME_DEVICE_ID=my-client

**Step 3: Start the server**

.. code-block:: bash

    docker compose -f docker-compose.server.yml build
    docker compose -f docker-compose.server.yml up -d

This starts:
  - Server API on port 8000
  - Qdrant vector database on port 6333
  - Metadata stored in Docker volumes

Wait for all containers to be healthy (check with ``docker compose logs -f``).

**Step 4: Start the client**

.. code-block:: bash

    docker compose -f docker-compose.client.yml build
    docker compose -f docker-compose.client.yml up -d

This starts the web UI on port 3000.

**Step 5: Verify**

Open http://localhost:3000 in your browser.
The dashboard should show the server is connected.

--------------------------------------------------------------------------

Configuration Reference
-----------------------

**Server Configuration (``.env.server``)**

.. list-table::
   :header-rows: 1
   :widths: 30 70 20

   * - Variable
     - Description
     - Default
   * - ``LOSEME_DEVICE_ID``
     - Unique identifier for this server device
     - ``server``
   * - ``QDRANT_URL``
     - Qdrant instance URL
     - ``http://qdrant:6333``
   * - ``LOSEME_EMBEDDING_MODEL``
     - Embedding model to use
     - ``sentence-transformer:all-MiniLM-L6-v2``
   * - ``LOSEME_CHUNKER``
     - Chunking strategy: simple, sentence, semantic
     - ``simple``
   * - ``LOSEME_VECTOR_STORAGE``
     - Vector storage backend: qdrant, qdrant-hybrid, in-memory
     - ``qdrant``
   * - ``LOSEME_API_KEY``
     - Optional API key for authentication
     - (empty)
   * - ``LOSEME_USE_CUDA``
     - Enable CUDA/GPU acceleration
     - ``false``

**Client Configuration (``.env.client``)**

.. list-table::
   :header-rows: 1
   :widths: 30 70 20

   * - Variable
     - Description
     - Default
   * - ``LOSEME_API_URL``
     - URL of the server API
     - ``http://localhost:8000``
   * - ``LOSEME_HOST_ROOT``
     - Host path to mount as container volume
     - - 
   * - ``LOSEME_CONTAINER_ROOT``
     - Container path for the mount
     - ``/mnt/userdata``
   * - ``LOSEME_DEVICE_ID``
     - Unique identifier for this client device
     - - 
   * - ``LOSEME_API_KEY``
     - API key matching server (if auth enabled)
     - - 

--------------------------------------------------------------------------

Embedding Models
-----------------

Configure via ``LOSEME_EMBEDDING_MODEL`` in ``.env.server``:

.. list-table:: Available Models
   :header-rows: 1
   :widths: 30 40 30

   * - Value
     - Model
     - Notes
   * - ``sentence-transformer:all-MiniLM-L6-v2``
     - MiniLM
     - Default, fast, CPU-friendly
   * - ``sentence-transformer:all-mpnet-base-v2``
     - MPNet
     - Better quality, slower
   * - ``nomic-ai/nomic-embed-text-v1``
     - Nomic
     - Good quality, requires trust_remote_code
   * - ``bge-m3``
     - BGE-M3
     - Hybrid (dense + sparse + ColBERT), GPU recommended

**Note:** BGE-M3 requires ``LOSEME_VECTOR_STORAGE=qdrant-hybrid``.

--------------------------------------------------------------------------

Chunking Strategies
-------------------

Configure via ``LOSEME_CHUNKER`` in ``.env.server``:

.. list-table:: Available Chunkers
   :header-rows: 1
   :widths: 25 25 50

   * - Value
     - Class
     - Description
   * - ``simple``
     - SimpleTextChunker
     - Fixed-size sliding window with overlap. Fast, no ML dependency.
   * - ``sentence``
     - SentenceAwareChunker
     - Splits on sentence boundaries. Never cuts mid-sentence.
   * - ``semantic``
     - SemanticChunker
     - Merges adjacent paragraphs by embedding similarity. Best quality, slowest.

--------------------------------------------------------------------------

Local Development Setup
-----------------------

For developing LoseMe (modifying code, running tests):

**Step 1: Clone and install dependencies**

.. code-block:: bash

    git clone <repository-url> loseme
    cd loseme
    
    # Install core package (editable)
    cd core && pip install -e . && cd ..
    
    # Install server dependencies
    cd server && pip install -e . && cd ..
    
    # Install client dependencies  
    cd client && pip install -e . && cd ..

**Step 2: Install Python dependencies**

.. code-block:: bash

    # Using poetry (recommended)
    poetry install
    
    # Or using pip
    pip install -r pyproject.toml

**Step 3: Set up environment**

.. code-block:: bash

    # Copy and edit environment files
    cp .env.server.example .env.server
    cp .env.client.example .env.client
    
    # Source the environment
    export $(cat .env.server | xargs)
    export $(cat .env.client | xargs)

**Step 4: Start services manually**

.. code-block:: bash

    # Start Qdrant (in background)
    docker run -d -p 6333:6333 -v qdrant_data:/qdrant/storage qdrant/qdrant
    
    # Start server
    cd server
    uvicorn api.app.main:app --host 0.0.0.0 --port 8000
    
    # In another terminal, start client
    cd client
    uvicorn web.main:app --host 0.0.0.0 --port 3000

--------------------------------------------------------------------------

Building Documentation
---------------------

To build this documentation locally:

.. code-block:: bash

    cd docs
    pip install -r requirements.txt
    make html

The built documentation will be in ``_build/html/``. Open ``index.html`` in your browser.

--------------------------------------------------------------------------

Troubleshooting
---------------

**GPU not detected**
  Ensure NVIDIA Container Toolkit is installed and Docker has GPU access.
  Verify with ``nvidia-smi`` and ``docker run --rm nvidia/cuda:12.1.1-base nvidia-smi``.

**Qdrant connection refused**
  Wait for Qdrant to initialize (can take 30+ seconds). Check logs with 
  ``docker compose logs qdrant``.

**Out of memory**
  Reduce batch sizes or use a smaller embedding model. The default MiniLM 
  requires ~2GB RAM for the model cache.

**Permission denied on mounted volumes**
  Ensure the host directory has read permissions for the Docker user (UID 1000).

**API connection failed**
  Verify the client can reach the server. In Docker Compose, use 
  ``http://server:8000`` as the API URL (not localhost).
