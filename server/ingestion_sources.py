"""
Server-side ingestion source management.

This module provides the server-side implementation of IngestionSource.from_scope
that can handle server-side sources like Paperless-ngx.
"""

from typing import Any, Callable
from loseme_core.models import IngestionSource
from loseme_core.paperless_model import PaperlessIndexingScope
from paperless_ingestion import PaperlessIngestionSource


def create_ingestion_source_from_scope(scope: Any, should_stop: Callable[[], bool]) -> IngestionSource:
    """
    Server-side factory to create the appropriate ingestion source based on scope type.
    
    This extends the core IngestionSource.from_scope to handle server-side sources.
    
    Args:
        scope: The indexing scope
        should_stop: Callable that returns True if ingestion should stop
        
    Returns:
        An IngestionSource instance appropriate for the scope type
    """
    # Handle Paperless scopes
    if hasattr(scope, 'type') and scope.type == "paperless":
        if isinstance(scope, PaperlessIndexingScope):
            return PaperlessIngestionSource(scope=scope, should_stop=should_stop)
        else:
            # Try to create a PaperlessIndexingScope from the data
            return PaperlessIngestionSource(scope=scope, should_stop=should_stop)
    
    # For all other scope types, use the core implementation
    return IngestionSource.from_scope(scope, should_stop)


# Monkey patch the core IngestionSource.from_scope to use our server-side implementation
original_from_scope = IngestionSource.from_scope

@classmethod
def server_from_scope(cls, scope: Any, should_stop: Callable[[], bool]) -> IngestionSource:
    """
    Server-side implementation of IngestionSource.from_scope.
    
    This method handles both client-side sources (filesystem, thunderbird) and
    server-side sources (paperless) appropriately.
    """
    return create_ingestion_source_from_scope(scope, should_stop)

# Replace the core method with our server-side implementation
IngestionSource.from_scope = server_from_scope


def get_ingestion_source(scope: Any, should_stop: Callable[[], bool]) -> IngestionSource:
    """
    Convenience function to get an ingestion source from a scope.
    
    Args:
        scope: The indexing scope
        should_stop: Callable that returns True if ingestion should stop
        
    Returns:
        An IngestionSource instance
    """
    return create_ingestion_source_from_scope(scope, should_stop)