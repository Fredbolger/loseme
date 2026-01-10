from src.domain.extraction.registry import ExtractorRegistry
from src.domain.extraction.plaintext import PlainTextExtractor

def build_extractor_registry() -> ExtractorRegistry:
    return ExtractorRegistry(
        extractors=[
            PlainTextExtractor(),
            # As the project evolves, additional extractors can be registered here.
            # PdfExtractor(),
            # ImageOcrExtractor(),
        ]
    )

