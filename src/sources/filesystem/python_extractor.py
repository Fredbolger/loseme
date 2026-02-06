from pathlib import Path
from src.sources.base.extractor import DocumentExtractor, DocumentExtractionResult
from src.sources.base.registry import extractor_registry

class PythonExtractor(DocumentExtractor):
    priority: int = 15

    def can_extract(self, path: Path) -> bool:
        return path.suffix.lower() == ".py"

    def extract(self, path: Path) -> DocumentExtractionResult:
        with open(path, 'r', encoding='utf-8') as file:
            text = file.read()

        return DocumentExtractionResult(
            text=text,
            content_type="text/x-python",
            metadata={
                "filename": path.name,
                "suffix": path.suffix,
                "num_lines": len(text.splitlines()),
            },
        )
    
    def can_extract_bytes(self, file_bytes: bytes) -> bool:
        # We won't implement byte extraction for Python files
        return False

extractor_registry.register_extractor(PythonExtractor())
