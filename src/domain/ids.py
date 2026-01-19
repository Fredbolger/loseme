from pathlib import Path
import hashlib
from uuid import UUID, uuid5

# Fixed namespace for the entire project.
# DO NOT CHANGE once data exists.
LOSEME_NAMESPACE = UUID("b1f7a8d6-9b9a-4a8a-bb6c-7e4e9c0f8d42")

def make_logical_document_id(
        text: str
)-> str:
        """
        Create a logical document ID based on the content of the document.
        This should be identical for documents with the same content, even if
        they come from different sources or paths, or even different OSes.
        """
        canonical_text = text.strip().encode("utf-8")
        canonical_hash = hashlib.sha256(canonical_text).hexdigest()
        logical_document_id = uuid5(
            LOSEME_NAMESPACE,
            canonical_hash
        ).hex
        return logical_document_id

def make_source_instance_id(
    source_type: str,
    device_id: str,
    source_path: Path,
) -> str:
    """
    Create a stable ID for a source instance (e.g., a file on a specific device).
    This will be used to track documents across indexing runs and pause/resume operations.
    """
    canonical_path = str(source_path.resolve())
    source_instance_id = hashlib.sha256(
        f"{source_type}:{device_id}:{canonical_path}".encode("utf-8")
        ).hexdigest()
    return source_instance_id

def make_chunk_id(
    document_id: str,
    document_checksum: str,
    index: int,
) -> str:
    name = f"{document_id}:{document_checksum}:{index}"
    return hashlib.sha256(name.encode("utf-8")).hexdigest()

def make_thunderbird_source_id(
    device_id: str,
    mbox_path: str,
    message_id: str,
) -> str:
    return hashlib.sha256(
        f"thunderbird:{device_id}:{mbox_path}:{message_id}".encode("utf-8")
    ).hexdigest()
