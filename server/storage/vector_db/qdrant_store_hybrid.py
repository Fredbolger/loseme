import uuid
import os
import io
import logging
import json
from typing import List, Tuple
from qdrant_client import QdrantClient, models
from qdrant_client.models import PointStruct, VectorParams, Distance, SparseVector, SparseIndexParams, MultiVectorConfig, MultiVectorComparator, SparseVectorParams, PointIdsList
from qdrant_client.http.exceptions import UnexpectedResponse

from loseme_core.config import EMBEDDING_MODEL
from loseme_core.models import Chunk
from wiring import build_embedding_provider
from loseme_core.domain import EmbeddingOutput
from storage.vector_db.vector_store import VectorStore
from storage.metadata_db.db import get_connection
from storage.vector_db.migrations import run_vector_migrations

COLLECTION = "chunks"
VECTOR_SIZE = build_embedding_provider().dimension()

logger = logging.getLogger(__name__)

def chunk_id_to_uuid(chunk_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))


class QdrantVectorStoreHybrid(VectorStore):
    def __init__(self, client: QdrantClient):
        self.client = client
        self.model_name = EMBEDDING_MODEL
        self.model = build_embedding_provider()
        self._ensure_collection()
        with get_connection() as conn:
            run_vector_migrations(conn, self.client, COLLECTION)
            
    def _ensure_collection(self) -> None:
        try:
            self.client.get_collection(COLLECTION)
        except UnexpectedResponse:
            logger.info(f"Creating Qdrant collection '{COLLECTION}' with vector size {VECTOR_SIZE}")
            self.client.create_collection(
                collection_name=COLLECTION,
                vectors_config={
                    "dense": VectorParams(
                    size=1024,
                    distance=Distance.COSINE,
                ),
                    "colbert": VectorParams(
                        size=1024,
                        distance=Distance.COSINE,
                        multivector_config=MultiVectorConfig(
                            comparator=MultiVectorComparator.MAX_SIM
                        ),
                    ),
                },
                sparse_vectors_config={
                    "sparse": SparseVectorParams(
                        index=SparseIndexParams(
                            on_disk=True,
                        ),
                    ),
                },
            )
    
    def add(self, chunk: Chunk, embedding: EmbeddingOutput) -> None:
        logger.debug(f"Adding chunk with ID {chunk.id} to Qdrant collection '{COLLECTION}'")
        logger.debug(f"Embedding has keys: {embedding.__dict__.keys()}")
        #self._ensure_collection()
        dense_vector = embedding.dense  # Assuming embedding.dense is a list of floats
        if len(dense_vector) != VECTOR_SIZE:
            raise ValueError(f"Vector size missmatch: expected {VECTOR_SIZE}, got {len(dense_vector)}")
        if not embedding.dense:
            raise ValueError("Dense embedding is required for hybrid vector store.")
        if not embedding.sparse:
            raise ValueError("Sparse embedding is required for hybrid vector store.")
        if not embedding.colbert_vec:
            raise ValueError("Colbert embedding is required for hybrid vector store.")

        qdrant_sparse_vector = self.create_sparse_vector(embedding.sparse)
        colbert_vector = embedding.colbert_vec  # Assuming colbert is a list of lists

        vector = {
            "dense": dense_vector,
            "colbert": colbert_vector,
            "sparse": qdrant_sparse_vector,
        }

        self.client.upsert(
            collection_name=COLLECTION,
            points=[
                PointStruct(
                    id=chunk_id_to_uuid(chunk.id),
                    vector=vector,
                    payload={
                        "chunk_id": chunk.id,
                        "text": chunk.text,
                        "source_type": chunk.source_type,
                        "source_path": chunk.source_path,
                        "document_part_id": chunk.document_part_id,
                        "device_id": chunk.device_id,
                        "index": chunk.index,
                        "metadata": chunk.metadata,
                        "unit_locator": chunk.unit_locator,
                    },
                )
            ],
        )
        return chunk_id_to_uuid(chunk.id)
    
    def create_sparse_vector(self, sparse_data):
        """Convert BGE-M3 sparse output to Qdrant sparse vector format"""
        sparse_indices = []
        sparse_values = []

        for key, value in sparse_data.items():
            # Only process positive values
            if float(value) > 0:
                # Handle string keys
                if isinstance(key, str):
                    if key.isdigit():
                        key = int(key)
                    else:
                        continue

                sparse_indices.append(key)
                sparse_values.append(float(value))

        return SparseVector(
            indices=sparse_indices,
            values=sparse_values
        )


    def search(
        self,
        query_embedding: EmbeddingOutput,
        top_k: int,
        prefetch_limit: int | None = None,
        score_threshold: float | None = None,
        dense_weight: float = 0.5,
        sparse_weight: float = 0.3,
    ) -> List[Tuple[Chunk, float]]:
        if prefetch_limit is None:
            prefetch_limit = max(top_k * 3, 100)

        if not query_embedding.dense:
            raise ValueError("Dense embedding is required.")
        if not query_embedding.sparse:
            raise ValueError("Sparse embedding is required.")
        if not query_embedding.colbert_vec:
            raise ValueError("ColBERT embedding is required.")

        sparse_vector = self.create_sparse_vector(query_embedding.sparse)

        hits = self.client.query_points(
            collection_name=COLLECTION,
            prefetch=[
                models.Prefetch(
                    prefetch=[
                        models.Prefetch(
                            query=sparse_vector,
                            using="sparse",
                            limit=prefetch_limit,
                        ),
                        models.Prefetch(
                            query=query_embedding.dense,
                            using="dense",
                            limit=prefetch_limit,
                        ),
                    ],
                    query=models.RrfQuery(rrf=models.Rrf(weights=[sparse_weight, dense_weight])),
                    limit=prefetch_limit,
                )
            ],
            # ColBERT re-ranks the weighted-RRF-fused pool
            query=query_embedding.colbert_vec,
            using="colbert",
            with_payload=True,
            limit=top_k,
            score_threshold=score_threshold,
        )

        results = []
        for hit in hits.points:
            chunk = Chunk(
                id=hit.payload["chunk_id"],
                source_type=hit.payload["source_type"],
                source_path=hit.payload["source_path"],
                text=hit.payload["text"] if "text" in hit.payload else "",
                document_part_id=hit.payload["document_part_id"],
                device_id=hit.payload["device_id"],
                index=hit.payload["index"],
                metadata=hit.payload.get("metadata", {}),
                unit_locator=hit.payload.get("unit_locator", ""),
            )
            results.append((chunk, hit.score if hit.score is not None else 0.0))

        return results

    def clear(self) -> None:
        if os.environ.get("ALLOW_VECTOR_CLEAR", "false").lower() != "1":
            raise PermissionError("Clearing the vector store is not allowed.")

        self.client.delete_collection(COLLECTION)
        self._ensure_collection()
    
    def dimension(self) -> int:
        return VECTOR_SIZE

    def query(self, vector: List[float], top_k: int = 10, prefetch_limit = None) -> List[Tuple[Chunk, float]]:
        return self.search(vector, top_k, prefetch_limit)
    
    def delete_collection(self) -> None:
        if os.environ.get("ALLOW_VECTOR_CLEAR", "false").lower() != "1":
            raise PermissionError("Deleting the vector store collection is not allowed.")
        self.client.delete_collection(COLLECTION)
    
    def retrieve_chunk_by_id(self, chunk_id: str) -> Chunk:
        """ 
        Retrieve a Chunk by its chunk_id from Qdrant.
        """ 
        point_id = chunk_id_to_uuid(chunk_id)
        result = self.client.retrieve(
            collection_name=COLLECTION,
            ids=[point_id],
            with_payload=True,
        )

        if result is None or len(result) == 0:
            logger.warning(f"Chunk with ID {chunk_id} not found in Qdrant collection '{COLLECTION}'")
            return None

        result = result[0]

        payload = result.payload
        chunk = Chunk(
            id=payload["chunk_id"],
            source_type=payload["source_type"],
            source_path=payload["source_path"],
            document_part_id=payload["document_part_id"],
            device_id=payload["device_id"],
            index=payload["index"],
            metadata=payload.get("metadata", {}),
            unit_locator=payload.get("unit_locator", "")
        )
        return chunk

    def count_chunks(self) -> int:
        self._ensure_collection()
        stats = self.client.get_collection(collection_name=COLLECTION)
        return stats.points_count
    
    def remove_chunks(self, chunk_ids: List[str]) -> None:
        point_ids = [chunk_id_to_uuid(cid) for cid in chunk_ids]
        self.client.delete(
            collection_name=COLLECTION,
            points_selector=PointIdsList(points=point_ids)
        )
    
    def export(self, file_path: str) -> io.BytesIO:
        """Export the entire collection as a stream."""
        export_result = self.client.export_collection(collection_name=COLLECTION)
        if not export_result.url:
            raise ValueError("Failed to get export URL from Qdrant.")
        
        # Download the exported file
        response = self.client._http_client.get(export_result.url)
        response.raise_for_status()
        
        return io.BytesIO(response.content)
