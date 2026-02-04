import uuid
import os
import logging
from typing import List, Tuple
from qdrant_client import QdrantClient, models
from qdrant_client.models import PointStruct, VectorParams, Distance, SparseVector, SparseIndexParams, MultiVectorConfig, MultiVectorComparator, SparseVectorParams
from qdrant_client.http.exceptions import UnexpectedResponse

from src.core.config import EMBEDDING_MODEL
from src.domain.models import Chunk
from src.core.wiring import build_embedding_provider
from src.domain.vector_store import VectorStore
from src.domain.embeddings import EmbeddingOutput

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
        self._ensure_collection()
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
                        "source_type": chunk.source_type,
                        "document_id": chunk.document_id,
                        "device_id": chunk.device_id,
                        "index": chunk.index,
                        "metadata": chunk.metadata,
                    },
                )
            ],
        )
    
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
        prefetch_limit = 10, 
    ) -> List[Tuple[Chunk, float]]:
        """
        Search for similar chunks.
        
        Returns:
            List of (chunk, score) tuples ordered by descending similarity
        """
        
        self._ensure_collection()

        if not query_embedding.dense:
            raise ValueError("Dense embedding is required for hybrid vector store search.")
        if not query_embedding.sparse:
            raise ValueError("Sparse embedding is required for hybrid vector store search.")
        if not query_embedding.colbert_vec:
            raise ValueError("Colbert embedding is required for hybrid vector store search.")

        dense_vector = query_embedding.dense
        sparse_vector = self.create_sparse_vector(query_embedding.sparse)
        colbert_vector = query_embedding.colbert_vec
        
        prefetch = [
                models.Prefetch(
                    query=sparse_vector,
                    using="sparse",
                    limit=prefetch_limit),
                models.Prefetch(
                    query=dense_vector,
                    using="dense",
                    limit=prefetch_limit),
                ]

        # perform re-ranking with colbert vectors
        hits = self.client.query_points(
                collection_name=COLLECTION,
                prefetch=prefetch,
                query=colbert_vector,
                using="colbert",
                with_payload=True,
                limit=top_k,
            )
    
        results = []
        for hit in hits.points:
            chunk = Chunk(
                id=hit.payload["chunk_id"],
                source_type = hit.payload["source_type"],
                document_id=hit.payload["document_id"],
                device_id=hit.payload["device_id"],
                index=hit.payload["index"],
                metadata=hit.payload.get("metadata", {}),
            )
            score = hit.score if hit.score is not None else 0.0
            results.append((chunk, score))
        
        return results        

    def clear(self) -> None:
        if os.environ.get("ALLOW_VECTOR_CLEAR", "false").lower() != "1":
            raise PermissionError("Clearing the vector store is not allowed.")

        self.client.delete_collection(COLLECTION)
        self._ensure_collection()
    
    def dimension(self) -> int:
        return VECTOR_SIZE

    def query(self, vector: List[float], top_k: int = 10) -> List[Tuple[Chunk, float]]:
        return self.search(vector, top_k)

    def remove_chunks(self, chunk_ids: List[str]) -> None:
        point_ids = [chunk_id_to_uuid(cid) for cid in chunk_ids]
        self.client.delete_points(
            collection_name=COLLECTION,
            points=point_ids
        )
    
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

        if result is None or not result[0].payload:
            raise ValueError(f"Chunk with id {chunk_id} not found in Qdrant.")
            
        result = result[0]

        payload = result.payload
        chunk = Chunk(
            id=payload["chunk_id"],
            source_type=payload["source_type"],
            document_id=payload["document_id"],
            device_id=payload["device_id"],
            index=payload["index"],
            metadata=payload.get("metadata", {}),
        )
        return chunk
