from pydantic import Field, BaseModel 
from pathlib import Path
from typing import Literal
from src.sources.base.models import Document, Chunk, IndexingScope, IngestionSource, IngestRequest
from src.sources.base.registry import indexing_scope_registry
import logging

logger = logging.getLogger(__name__)

class FilesystemIndexingScope(IndexingScope):
    type: Literal["filesystem"] = "filesystem"

    directories: list[Path] = Field(default_factory=list)
    recursive: bool = True
    include_patterns: list[str] = Field(default_factory=list)
    exclude_patterns: list[str] = Field(default_factory=list)

    def normalized(self) -> dict:
        return {
            "directories": sorted(str(p.resolve()) for p in self.directories),
            "include_patterns": sorted(self.include_patterns),
            "exclude_patterns": sorted(self.exclude_patterns),
        }

    def hash(self) -> str:
        normalized_json = json.dumps(self.normalized(), sort_keys=True)
        return hashlib.sha256(normalized_json.encode()).hexdigest()

    def serialize(self) -> dict:
        return {
            "type": self.type,
            "directories": [str(p) for p in self.directories],
            "recursive": self.recursive,
            "include_patterns": self.include_patterns,
            "exclude_patterns": self.exclude_patterns,
        }
    
    def locator(self) -> str:
        dir_list = ",".join(sorted(str(p.resolve()) for p in self.directories))
        return f"filesystem:{dir_list}"

    @classmethod
    def deserialize(cls, data: dict) -> "FilesystemIndexingScope":
        raw_dirs = data.get("directories", [])
        logger.debug(f"Deserializing directories: {raw_dirs!r}")

        if isinstance(raw_dirs, (str, Path)):
            raw_dirs = [raw_dirs]

        if not isinstance(raw_dirs, list):
            raise ValueError("directories must be a path or list of paths")

        directories = [Path(p) for p in raw_dirs]

        # Guard against character explosion (belt + suspenders)
        if any(len(str(p)) == 1 for p in directories):
            raise ValueError(f"Invalid directories value: {raw_dirs!r}")
        
        return cls(
            directories=directories,
            recursive=data.get("recursive", True),
            include_patterns=data.get("include_patterns", []),
            exclude_patterns=data.get("exclude_patterns", []),
        )

class FilesystemIngestRequest(BaseModel):
    directories: list[str] = []
    recursive: bool = True
    include_patterns: list[str] = []
    exclude_patterns: list[str] = []

indexing_scope_registry.register_scope("filesystem", FilesystemIndexingScope)
