from pathlib import Path
from pipeline.extraction.base import DocumentExtractor, DocumentExtractionResult

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
