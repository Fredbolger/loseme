import os
from abc import ABC, abstractmethod
from pydantic import BaseModel

class IndexingScope(BaseModel):
    """ 
    Abstract base class for indexing scopes.
    Based on the type field in the dictionary, the appropriate subclass will be instantiated.
    """
    type: str
    
    @abstractmethod
    def locator(self) -> str:
        """Return a locator that uniquely identifies the source of this scope."""
        pass
    
    @abstractmethod
    def serialize(self) -> dict:
        """Serialize the scope to a dictionary."""
        pass

    @classmethod
    def deserialize(cls, data: dict) -> "IndexingScope":
        scope_type = data.get("type")

        if scope_type == "filesystem":
            from .filesystem_model import FilesystemIndexingScope
            #return indexing_scope_registry.deserialize(data)
            return FilesystemIndexingScope.deserialize(data)

        if scope_type == "thunderbird":
            #return indexing_scope_registry.deserialize(data)
            from .thunderbird_model import ThunderbirdIndexingScope
            return ThunderbirdIndexingScope.deserialize(data)

        raise ValueError(f"Unknown scope type: {scope_type}")


