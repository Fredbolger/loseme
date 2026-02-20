import uuid
import os
import logging
from typing import List, Tuple
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance, PointIdsList
from qdrant_client.http.exceptions import UnexpectedResponse

from src.core.config import EMBEDDING_MODEL
from src.sources.base.models import Chunk
from src.core.wiring import build_embedding_provider
from src.domain.embeddings import EmbeddingOutput
from storage.vector_db.vector_store import VectorStore

COLLECTION = "chunks"
VECTOR_SIZE = build_embedding_provider().dimension()

logger = logging.getLogger(__name__)

def chunk_id_to_uuid(chunk_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))


class QdrantVectorStore(VectorStore):
    def __init__(self, client: QdrantClient):
        self.client = client
        self.model_name = EMBEDDING_MODEL
        self._ensure_collection()
    
    def _ensure_collection(self) -> None:
        try:
            logger.debug(f"Checking for Qdrant collection '{COLLECTION}'")
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
    
    def add(self, chunk: Chunk, embedding: EmbeddingOutput) -> None:
        logger.debug(f"Adding chunk with id {chunk.id} to Qdrant collection '{COLLECTION}'")
        self._ensure_collection()
        vector = embedding.dense 
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
                        "source_type": chunk.source_type,
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
            query=query_vector.dense,
            limit=top_k,
        )

        results = []
        for hit in hits.points:
            chunk = Chunk(
                id=hit.payload["chunk_id"],
                source_type = hit.payload["source_type"],
                document_part_id=hit.payload["document_part_id"],
                device_id=hit.payload["device_id"],
                index=hit.payload["index"],
                metadata=hit.payload.get("metadata", {}),
                unit_locator=hit.payload.get("unit_locator", "")
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
            logger.warning(f"Chunk with id {chunk_id} not found in Qdrant.")
            return None
            
        result = result[0]

        payload = result.payload
        chunk = Chunk(
            id=payload["chunk_id"],
            source_type=payload["source_type"],
            document_part_id=payload["document_part_id"],
            device_id=payload["device_id"],
            index=payload["index"],
            metadata=payload.get("metadata", {}),
            unit_locator=payload.get("unit_locator", "")
        )
        return chunk
    
    def count_chunks(self) -> int:
        self._ensure_collection()
        info = self.client.get_collection(COLLECTION)
        return info.points_count
    
    def remove_chunks(self, chunk_ids: List[str]) -> None:
        point_ids = [chunk_id_to_uuid(cid) for cid in chunk_ids]
        self.client.delete(
            collection_name=COLLECTION,
            points_selector=PointIdsList(points=point_ids)
        )

    def chunk_exists(self, chunk_id: str) -> bool:
        point_id = chunk_id_to_uuid(chunk_id)
        result = self.client.retrieve(
            collection_name=COLLECTION,
            ids=[point_id],
            with_payload=False,
        )
        return result is not None and len(result) > 0 
