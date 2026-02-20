from pathlib import Path
from src.sources.base.extractor import DocumentExtractor, DocumentExtractionResult
from src.sources.base.registry import extractor_registry

class PythonExtractor(DocumentExtractor):
    name: str = "python"
    priority: int = 15
    supported_mime_types: set[str] = {"text/x-python"}
    version: str = "0.1"

    def can_extract(self, path: Path) -> bool:
        return path.suffix.lower() == ".py"
    
    def can_extract_content_type(self, content_type: str) -> bool:
        return content_type.lower() == "text/x-python"

    def extract(self, path: Path) -> DocumentExtractionResult:
        with open(path, 'r', encoding='utf-8') as file:
            text = file.read()

        return DocumentExtractionResult(
            texts=[text],
            content_types=["text/x-python"],
            metadata=[{
                "filename": path.name,
                "suffix": path.suffix,
                "num_lines": len(text.splitlines()),
            }],
            unit_locators=[f"filesytem:{path.resolve()}"],
            extractor_names=[self.name],
            extractor_versions=[self.version],
        )
    
    def can_extract_bytes(self, file_bytes: bytes) -> bool:
        # We won't implement byte extraction for Python files
        return False

extractor_registry.register_extractor(PythonExtractor())
