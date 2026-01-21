import uuid
import os
import logging
from typing import List, Tuple
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from qdrant_client.http.exceptions import UnexpectedResponse

from src.domain.models import Chunk
from src.core.wiring import build_embedding_provider
from src.domain.vector_store import VectorStore

COLLECTION = "chunks"
VECTOR_SIZE = build_embedding_provider().dimension()

logger = logging.getLogger(__name__)

def chunk_id_to_uuid(chunk_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))


class QdrantVectorStore(VectorStore):
    def __init__(self, client: QdrantClient):
        self.client = client
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        try:
            self.client.get_collection(COLLECTION)
        except UnexpectedResponse:
            logger.info(f"Creating Qdrant collection '{COLLECTION}' with vector size {VECTOR_SIZE}")
            self.client.create_collection(
                collection_name=COLLECTION,
                vectors_config=VectorParams(
                    size=VECTOR_SIZE,
                    distance=Distance.COSINE,
                ),
            )
    
    def add(self, chunk: Chunk, vector: List[float]) -> None:
        self._ensure_collection()
        if len(vector) != VECTOR_SIZE:
            raise ValueError(f"Vector size missmatch: expected {VECTOR_SIZE}, got {len(vector)}")
        self.client.upsert(
            collection_name=COLLECTION,
            points=[
                PointStruct(
                    id=chunk_id_to_uuid(chunk.id),
                    vector=vector,
                    payload={
                        "chunk_id": chunk.id,
                        "document_id": chunk.document_id,
                        "device_id": chunk.device_id,
                        "index": chunk.index,
                        "metadata": chunk.metadata,
                    },
                )
            ],
        )
    def search(
        self, 
        query_vector: List[float], 
        top_k: int
    ) -> List[Tuple[Chunk, float]]:
        """
        Search for similar chunks.
        
        Returns:
            List of (chunk, score) tuples ordered by descending similarity
        """
        self._ensure_collection()

        hits = self.client.query_points(
            collection_name=COLLECTION,
            query=query_vector,
            limit=top_k,
        )

        results = []
        for hit in hits.points:
            chunk = Chunk(
                id=hit.payload["chunk_id"],
                document_id=hit.payload["document_id"],
                device_id=hit.payload["device_id"],
                index=hit.payload["index"],
                metadata=hit.payload.get("metadata", {}),
            )
            # Qdrant returns similarity scores, higher = more similar
            score = hit.score if hasattr(hit, 'score') else 0.0
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
