from loseme_core.models import IndexingScope

class StoredScope(IndexingScope):
    """Concrete scope used server-side just for carrying scope JSON data."""
    model_config = {"extra": "allow"}

    def locator(self) -> str:
        return self.type
    
    def serialize(self) -> dict:
        return self.model_dump()

