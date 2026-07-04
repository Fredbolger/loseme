Client API
==========

The client provides both a CLI and web UI for interacting with the LoseMe system.
This page documents the client-side components.

--------------------------------------------------------------------------

CLI Modules
-----------

The CLI is built with Typer and provides commands for ingestion, search, and 
source management.

.. automodule:: client.cli.main
   :members:

.. automodule:: client.cli.ingest
   :members:

.. automodule:: client.cli.sources
   :members:

.. automodule:: client.cli.config
   :members:

Extractors
---------

Document extractors are responsible for pulling text and metadata from 
different file types.

Available extractors:

- **PDFExtractor**: Extracts text from PDF files
- **PlaintextExtractor**: Extracts text from plain text files
- **HTMLExtractor**: Extracts text from HTML files
- **EMLExtractor**: Extracts text and metadata from email files
- **ThunderbirdExtractor**: Extracts from Thunderbird mailbox files
- **PythonExtractor**: Extracts from Python source files

.. automodule:: client.extractors.extractor
   :members:

.. automodule:: client.extractors.pdf_extractor
   :members:

.. automodule:: client.extractors.plaintext_extractor
   :members:

.. automodule:: client.extractors.html_extractor
   :members:

.. automodule:: client.extractors.eml_extractor
   :members:

.. automodule:: client.extractors.thunderbird_extractor
   :members:

.. automodule:: client.extractors.python_extractor
   :members:

.. automodule:: client.extractors.registry
   :members:

Sources
------

Ingestion sources discover and read documents from various sources.

.. automodule:: client.sources.filesystem.filesystem_source
   :members:

.. automodule:: client.sources.thunderbird.thunderbird_source
   :members:

.. automodule:: client.sources.base.docker_path_translation
   :members:

Ingest
-----

Queue client for sending document parts to the server.

.. automodule:: client.ingest.queue_client
   :members:

Web
---

The web UI is a FastAPI application that provides the dashboard and search interface.

.. automodule:: client.web.main
   :members:

.. automodule:: client.web.preview_proxy
   :members:

Preview
------

Client-side preview generators for rendering documents in the browser.

.. automodule:: client.preview.models
   :members:

.. automodule:: client.preview.registry
   :members:

.. automodule:: client.preview.generators.plaintext
   :members:

.. automodule:: client.preview.generators.eml
   :members:

.. automodule:: client.preview.generators.thunderbird
   :members:
