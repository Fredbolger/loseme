import json
from storage.metadata_db.db import execute, fetch_one
from src.domain.models import Document

def upsert_document(doc: Document) -> None:
    execute(
        """
        INSERT INTO documents (
            document_id,
            logical_checksum,
            source_type,
            source_instance_id,
            device_id,
            source_path,
            docker_path,
            metadata_json,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(document_id) DO UPDATE SET
            source_path = excluded.source_path,
            metadata_json = excluded.metadata_json,
            updated_at = excluded.updated_at
        """,
        (
            doc.id,
            doc.checksum,
            doc.source_type,
            doc.source_id,
            doc.device_id,
            doc.source_path,
            doc.docker_path,
            json.dumps(doc.metadata),
            doc.created_at.isoformat(),
            doc.updated_at.isoformat(),
        ),
    )

def get_document(document_id: str):
    row = fetch_one(
        "SELECT * FROM documents WHERE document_id = ?",
        (document_id,),
    )
    return dict(row) if row else None

