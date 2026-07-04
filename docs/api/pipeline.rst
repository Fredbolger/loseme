Pipeline
========

The processing pipeline is responsible for transforming documents into 
searchable vector embeddings.

Chunking
--------

Chunking splits documents into smaller, semantically meaningful units that 
are easier to process and search.

Available chunkers:

- **SimpleTextChunker**: Fixed-size sliding window with overlap. Fast, no ML dependency.
- **SentenceAwareChunker**: Splits on sentence boundaries. Never cuts mid-sentence.
- **SemanticChunker**: Merges adjacent paragraphs by embedding similarity. Best quality.

.. automodule:: server.pipeline.chunking.simple_chunker
   :members:

.. automodule:: server.pipeline.chunking.sentence_chunker
   :members:

.. automodule:: server.pipeline.chunking.semantic_chunker
   :members:

Embeddings
----------

Embedding transforms text chunks into vector representations that can be 
searched using similarity metrics.

Available embedding providers:

- **SentenceTransformerEmbeddingProvider**: HuggingFace Sentence Transformers
- **NomicEmbeddingProvider**: Nomic embedding models
- **BGEM3EmbeddingProvider**: Hybrid dense + sparse + ColBERT embeddings
- **DummyEmbeddingProvider**: Test/fallback (deterministic dummy embeddings)

.. automodule:: server.pipeline.embeddings.sentence_transformer
   :members:

.. automodule:: server.pipeline.embeddings.nomic
   :members:

.. automodule:: server.pipeline.embeddings.bgem3
   :members:

.. automodule:: server.pipeline.embeddings.dummy
   :members:

