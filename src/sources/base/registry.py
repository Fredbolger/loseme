from pathlib import Path
from typing import Optional, List, Dict, Type
from src.sources.base.extractor import DocumentExtractor, DocumentExtractionResult
from src.sources.base.models import IndexingScope
import logging

logger = logging.getLogger(__name__)

class ExtractorRegistry:
    #def __init__(self, extractors: List[DocumentExtractor]):
    def __init__(self, extractors: Optional[List[DocumentExtractor]] = None):
        if extractors is None:
            extractors = []
        self.extractors = sorted(
            extractors, key=lambda e: e.priority, reverse=True
        )

    def extract(self, path: Path) -> Optional[DocumentExtractionResult]:
        for extractor in self.extractors:
            if extractor.can_extract(path):
                logger.debug(f"Using extractor {extractor.__class__.__name__} for path {path}")
                return extractor.extract(path)
            else:
                logger.debug(f"Extractor {extractor.__class__.__name__} cannot handle path {path}")
        return None

    def extract_from_bytes(self, file_bytes: bytes) -> Optional[DocumentExtractionResult]:
        for extractor in self.extractors:
            if extractor.can_extract_bytes(file_bytes):
                return extractor.extract_from_bytes(file_bytes)
            else:
                logger.debug(f"Extractor {extractor.__class__.__name__} cannot handle content type {content_type}")
        return None
    
    def get_extractor(self, name: str) -> Optional[DocumentExtractor]:
        for extractor in self.extractors:
            if extractor.name == name:
                return extractor
        return None
    
    def register_extractor(self, extractor: DocumentExtractor):
        self.extractors.append(extractor)
        self.extractors.sort(key=lambda e: e.priority, reverse=True)
    
    def list_extractors(self) -> List[str]:
        return [extractor.name for extractor in self.extractors]

class IndexingScopeRegistry():
    def __init__(self):
        self._types: Dict[str, Type[IndexingScope]] = {}

    def register_scope(self, scope_type: str, cls: Type[IndexingScope]) -> None:
        self._types[scope_type] = cls

    def deserialize(self, data: dict) -> IndexingScope:
        scope_type = data.get("type")
        if not scope_type or scope_type not in self._types:
            raise ValueError(f"Unknown indexing scope type: {scope_type}")
        cls = self._types[scope_type]
        return cls.deserialize(data)

    def get_scope(self, scope_type: str):
        return self._types.get(scope_type)


class IngestionSourceRegistry():
    def __init__(self):
        self._sources: Dict[str, Type] = {}

    def register_source(self, source_type: str, cls: Type) -> None:
        self._sources[source_type] = cls

    def get_source(self, source_type: str):
        return self._sources.get(source_type)

extractor_registry = ExtractorRegistry()
indexing_scope_registry = IndexingScopeRegistry()
ingestion_source_registry = IngestionSourceRegistry()
