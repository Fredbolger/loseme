from pathlib import Path
from typing import Optional, List
from .base import DocumentExtractor, DocumentExtractionResult

class ExtractorRegistry:
    def __init__(self, extractors: List[DocumentExtractor]):
        self.extractors = extractors

    def extract(self, path: Path) -> Optional[DocumentExtractionResult]:
        for extractor in self.extractors:
            if extractor.can_extract(path):
                return extractor.extract(path)
        return None

