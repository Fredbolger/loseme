from pathlib import Path
from src.sources.base.docker_path_translation import host_path_to_container
from api.preview.registry import PreviewGenerator, preview_registry
from api.preview.models import PreviewResult

_SUFFIX_TO_LANGUAGE = {
    ".md":  "markdown",
    ".rst": "restructuredtext",
    ".txt": "plaintext",
    ".py":  "python",
    ".js":  "javascript",
    ".ts":  "typescript",
    ".css": "css",
    ".html": "html",
}

_SUPPORTED = set(_SUFFIX_TO_LANGUAGE.keys())


class PlaintextPreviewGenerator(PreviewGenerator):
    name = "plaintext"
    priority = 10

    def can_handle(self, source_type: str, doc_part: dict) -> bool:
        if source_type != "filesystem":
            return False
        suffix = Path(doc_part.get("source_path", "")).suffix.lower()
        return suffix in _SUPPORTED

    def generate(self, doc_part: dict) -> PreviewResult:
        host_path = doc_part["source_path"]
        path = Path(host_path_to_container(host_path))
        suffix = path.suffix.lower()
        text = path.read_text(encoding="utf-8", errors="replace")
        return PreviewResult(
            source_type="filesystem",
            preview_type="plaintext",
            text=text,
            language=_SUFFIX_TO_LANGUAGE.get(suffix, "plaintext"),
        )


preview_registry.register(PlaintextPreviewGenerator())
