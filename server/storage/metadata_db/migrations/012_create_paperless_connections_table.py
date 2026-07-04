"""
Migration 012: Create paperless_connections table for Paperless-ngx integration.

This migration creates the paperless_connections table which stores connection
credentials for Paperless-ngx instances. Credentials are stored server-side and
never duplicated in other tables.
"""


def run(conn):
    """Create the paperless_connections table."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS paperless_connections (
            id TEXT PRIMARY KEY,
            base_url TEXT NOT NULL,
            api_token TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
    conn.commit()