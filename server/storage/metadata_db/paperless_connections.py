"""
Paperless-ngx connection management and CRUD operations.

This module provides database operations for Paperless-ngx connections.
Credentials are stored here and never duplicated elsewhere in the system.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import uuid
import logging

from storage.metadata_db.db import get_connection, execute, fetch_one, fetch_all

logger = logging.getLogger(__name__)

# SQL for creating the paperless_connections table
CREATE_PAPERLESS_CONNECTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS paperless_connections (
    id TEXT PRIMARY KEY,
    base_url TEXT NOT NULL,
    api_token TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


class PaperlessConnection:
    """Represents a Paperless-ngx connection."""
    
    def __init__(self, 
                 id: str, 
                 base_url: str, 
                 api_token: str, 
                 created_at: str, 
                 updated_at: str):
        self.id = id
        self.base_url = base_url
        self.api_token = api_token
        self.created_at = created_at
        self.updated_at = updated_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "base_url": self.base_url,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            # Note: api_token is intentionally excluded from serialization for security
        }
    
    @classmethod
    def from_row(cls, row) -> "PaperlessConnection":
        """Create a PaperlessConnection from a database row."""
        return cls(
            id=row["id"],
            base_url=row["base_url"],
            api_token=row["api_token"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


def init_paperless_connections() -> None:
    """Initialize the paperless_connections table if it doesn't exist."""
    with get_connection() as conn:
        conn.execute(CREATE_PAPERLESS_CONNECTIONS_TABLE)
        conn.commit()


def create_paperless_connection(base_url: str, api_token: str) -> PaperlessConnection:
    """
    Create a new Paperless-ngx connection.
    
    Args:
        base_url: The base URL of the Paperless-ngx instance (e.g., "https://paperless.example.com")
        api_token: The API token for authentication
        
    Returns:
        The created PaperlessConnection object
    """
    connection_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    query = """
    INSERT INTO paperless_connections (id, base_url, api_token, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?)
    """
    
    with get_connection() as conn:
        conn.execute(query, (connection_id, base_url, api_token, now, now))
        conn.commit()
    
    logger.info(f"Created Paperless connection {connection_id} for {base_url}")
    
    return PaperlessConnection(
        id=connection_id,
        base_url=base_url,
        api_token=api_token,
        created_at=now,
        updated_at=now,
    )


def get_paperless_connection(connection_id: str) -> Optional[PaperlessConnection]:
    """
    Get a Paperless-ngx connection by ID.
    
    Args:
        connection_id: The ID of the connection to retrieve
        
    Returns:
        The PaperlessConnection object, or None if not found
    """
    query = "SELECT * FROM paperless_connections WHERE id = ?"
    row = fetch_one(query, (connection_id,))
    
    if row is None:
        logger.debug(f"Paperless connection with ID {connection_id} not found")
        return None
    
    return PaperlessConnection.from_row(row)


def get_paperless_connection_by_url(base_url: str) -> Optional[PaperlessConnection]:
    """
    Get a Paperless-ngx connection by its base URL.
    
    Args:
        base_url: The base URL of the Paperless-ngx instance
        
    Returns:
        The PaperlessConnection object, or None if not found
    """
    query = "SELECT * FROM paperless_connections WHERE base_url = ?"
    row = fetch_one(query, (base_url,))
    
    if row is None:
        logger.debug(f"Paperless connection with base URL {base_url} not found")
        return None
    
    return PaperlessConnection.from_row(row)


def list_paperless_connections() -> List[PaperlessConnection]:
    """
    List all Paperless-ngx connections.
    
    Returns:
        List of all PaperlessConnection objects
    """
    query = "SELECT * FROM paperless_connections ORDER BY created_at DESC"
    rows = fetch_all(query)
    
    return [PaperlessConnection.from_row(row) for row in rows]


def update_paperless_connection(connection_id: str, 
                                  base_url: Optional[str] = None,
                                  api_token: Optional[str] = None) -> Optional[PaperlessConnection]:
    """
    Update an existing Paperless-ngx connection.
    
    Args:
        connection_id: The ID of the connection to update
        base_url: New base URL (optional)
        api_token: New API token (optional)
        
    Returns:
        The updated PaperlessConnection object, or None if not found
    """
    # Get the existing connection
    existing = get_paperless_connection(connection_id)
    if existing is None:
        logger.warning(f"Cannot update Paperless connection with ID {connection_id}: not found")
        return None
    
    # Use existing values for fields not being updated
    updated_base_url = base_url if base_url is not None else existing.base_url
    updated_api_token = api_token if api_token is not None else existing.api_token
    updated_at = datetime.now(timezone.utc).isoformat()
    
    query = """
    UPDATE paperless_connections 
    SET base_url = ?, api_token = ?, updated_at = ?
    WHERE id = ?
    """
    
    with get_connection() as conn:
        conn.execute(query, (updated_base_url, updated_api_token, updated_at, connection_id))
        conn.commit()
    
    logger.info(f"Updated Paperless connection {connection_id}")
    
    return PaperlessConnection(
        id=connection_id,
        base_url=updated_base_url,
        api_token=updated_api_token,
        created_at=existing.created_at,
        updated_at=updated_at,
    )


def delete_paperless_connection(connection_id: str) -> bool:
    """
    Delete a Paperless-ngx connection.
    
    Args:
        connection_id: The ID of the connection to delete
        
    Returns:
        True if the connection was deleted, False if not found
    """
    # First check if it exists
    existing = get_paperless_connection(connection_id)
    if existing is None:
        logger.warning(f"Cannot delete Paperless connection with ID {connection_id}: not found")
        return False
    
    query = "DELETE FROM paperless_connections WHERE id = ?"
    
    with get_connection() as conn:
        conn.execute(query, (connection_id,))
        conn.commit()
    
    logger.info(f"Deleted Paperless connection {connection_id}")
    return True


def validate_paperless_connection(connection_id: str) -> bool:
    """
    Validate that a Paperless-ngx connection is working by testing the API.
    
    Args:
        connection_id: The ID of the connection to validate
        
    Returns:
        True if the connection is valid, False otherwise
    """
    connection = get_paperless_connection(connection_id)
    if connection is None:
        logger.warning(f"Cannot validate Paperless connection with ID {connection_id}: not found")
        return False
    
    # Import the API client here to avoid circular imports
    try:
        from paperless_api_client import PaperlessApiClient
        client = PaperlessApiClient(base_url=connection.base_url, api_token=connection.api_token)
        return client.test_connection()
    except Exception as e:
        logger.error(f"Error validating Paperless connection {connection_id}: {str(e)}")
        return False


def get_connection_url_and_token(connection_id: str) -> Optional[tuple]:
    """
    Get the base URL and API token for a connection.
    
    This is a convenience method for when you need both values together.
    
    Args:
        connection_id: The ID of the connection
        
    Returns:
        Tuple of (base_url, api_token) or None if connection not found
    """
    connection = get_paperless_connection(connection_id)
    if connection is None:
        return None
    
    return (connection.base_url, connection.api_token)
