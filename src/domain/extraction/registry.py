from pathlib import Path
from typing import Optional, List
from .base import DocumentExtractor, DocumentExtractionResult
import logging

logger = logging.getLogger(__name__)

class ExtractorRegistry:
    def __init__(self, extractors: List[DocumentExtractor]):
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

