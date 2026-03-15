from dataclasses import dataclass, field
from typing import Optional

@dataclass
class PreviewResult:
    """
    Standardised envelope returned by every PreviewGenerator.
    Add fields here as new preview types need them — old generators
    just leave new fields as None.
    """
    source_type: str              # e.g. "thunderbird", "filesystem"
    preview_type: str             # e.g. "email", "plaintext", "pdf"

    # Email fields
    subject:   Optional[str] = None
    from_:     Optional[str] = None
    to:        Optional[str] = None
    date:      Optional[str] = None
    body_html: Optional[str] = None
    body_text: Optional[str] = None

    # Plaintext / code
    text:      Optional[str] = None
    language:  Optional[str] = None   # e.g. "markdown", "python"

    # Generic metadata blob — catch-all for future types
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}
