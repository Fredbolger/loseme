import uuid
import os
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from qdrant_client.http.exceptions import UnexpectedResponse

from src.domain.models import Chunk
from storage.vector_db.base import VectorStore


COLLECTION = "chunks"
VECTOR_SIZE = 384  # must match embedding size
# ⚠️ Changing VECTOR_SIZE requires manual collection recreation

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
            self.client.create_collection(
                collection_name=COLLECTION,
                vectors_config=VectorParams(
                    size=VECTOR_SIZE,
                    distance=Distance.COSINE,
                ),
            )
    
    def add(self, chunk: Chunk, vector: list[float]) -> None:
        self._ensure_collection()

        self.client.upsert(
            collection_name=COLLECTION,
            points=[
                PointStruct(
                    id=chunk_id_to_uuid(chunk.id),
                    vector=vector,
                    payload={
                        "chunk_id": chunk.id,
                        "document_id": chunk.document_id,
                        "document_checksum": chunk.document_checksum,
                        "index": chunk.index,
                        "content": chunk.content,
                        "metadata": chunk.metadata,
                    },
                )
            ],
        )

    def search(self, query_vector: list[float], top_k: int) -> list[Chunk]:
        self._ensure_collection()

        hits = self.client.query_points(
            collection_name=COLLECTION,
            query=query_vector,
            limit=top_k,
        )

        return [
            Chunk(
                id=hit.payload["chunk_id"],
                document_id=hit.payload["document_id"],
                document_checksum=hit.payload["document_checksum"],
                index=hit.payload["index"],
                content=hit.payload["content"],
                metadata=hit.payload.get("metadata", {}),
            )
            for hit in hits.points
        ]

    def clear(self) -> None:
        if os.environ.get("ALLOW_VECTOR_CLEAR", "false").lower() != "1":
            raise PermissionError("Clearing the vector store is not allowed.")

        self.client.delete_collection(COLLECTION)
        self._ensure_collection()

