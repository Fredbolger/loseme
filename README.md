# Local Semantic Memory

**Local-first semantic search over personal data**

## What is this?

Local Semantic Memory is a privacy-preserving system that lets you search your personal files by *meaning*, not just filenames or keywords. It runs entirely on your own devices.

Think of it as a personal knowledge base that understands what your documents are about, making everything you've ever written/mailed/developed easily searchable by content.

However, the prupsoe is not to introduce an *addiitonal* storage system, but only provide a sematic indexing database. After a search the original files can be openend for e.g. by a local editing tool or thw browser.

## Architecture

The system follows a modular pipeline:

```
Filesystem → Extraction → Chunking → Embedding → Vector DB → Search
```

### Key Design Decisions

1. **Local-first**: All processing happens on your machine. Data should not leave your control.


2. **Multi-device aware**: The system tracks which device indexed which files and should allow for multiple devices containing the same documents, possibly at different paths. For such documents, no duplicate embeddings should be created. 

3. **Source-instance identity**: The `source_instance_id` is a unique idetifier constructed from the ¸`source_type` (e.g. 'filesystem') and the `device_id` and the `source_path` (e.g. '/home/user/docs').
 
4. **Document-part identity**: Documents are split into document parts, this allows e.g. emails to consist of multiple parts and return a matching for the sub-parts. The `logical_document_part_id` is created from the `source_instance_id` and the `unit_locator`, identifying the part. 

5. **Resumable processing**: Indexing runs can be interrupted and resumed without reprocessing documents.

6. **Dockerized**: Everything runs in containers for reproducibility and easy deployment.

## Quick Start

```bash
# Start all relevant 
docker-compose up -d qdrant api web_client

# Ingest a directory
poetry run python -m clients.cli.main ingest /data/my-documents

# Search semantically
poetry run pyton search "machine learning concepts" --top-k 5

# Search interactively (open the selected file)
poetry run python -m clients.cli.main search "machine learning concepts" --interactive
```


## How It Works

1. **File Discovery**: Files are discovered based on `Sources`. These sources return an iterator object which yields a `Document`. 


2. **Content Extraction**: The content of each `Document` is extracted based on a global `ExtractorRegistry` which maps file types to extractor functions (e.g., PDF, DOCX, TXT). If no extractor is found, the file is skipped. 


3. **Multipart Documents**: If a `Source` allows multipart documents, it can split a document into multiple logical parts (e.g., an email with attachments). Each part is treated as a separate unit for embedding and search. These parts are upserted to the `document_parts_qeue`


4. **Chunking**: During ingestion, each `DocumentPart` is retrieved from the `document_parts_queue` and processed. Each `DocumentPart` is split into smaller chunks by one of the implemented `Chunker` classes. 

5. **Embedding**: Each chunk is converted into a vector embedding using the available `EmbeddingProviders'. The resulting embeddings are stored in the `Qdrant` vector database, while metadata about the document and its parts are stored in a local `SQLite` database.

6. **Search**: When a search query is made, it is also converted into an embedding and compared against the stored embeddings in `Qdrant`. The most relevant document parts are retrieved based on cosine similarity. 


7. **(Optional) Re-Ranking**: Depending on the applied `EmbeddingProvider` a re-ranking of the search results can be applied.


## Project Structure

```
semantic-memory/

├── src/              # Main source code
├── api/              # FastAPI server
├── pipeline/         # Processing stages (chunking, embeddings)
├── storage/          # Vector DB and metadata DB
├── scripts/          # Indexing and maintenance scripts
├── clients/          # CLI and web client
└── tests/            # Comprehensive test suite
```

## Technology Stack

- **Python 3.11+**
- **FastAPI** for the API layer
- **Qdrant** for vector storage
- **SQLite** for metadata
- **Docker** for deployment

## Contributing

This project prioritizes clean, understandable code. Each module is independent and testable.

## License
This project is licensed under the AGPLv3 License. See the [gnu website](https://www.gnu.org/licenses/agpl-3.0.en.html) for details.
