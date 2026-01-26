from dataclasses import dataclass

@dataclass
class OpenDescriptor:
    source_type: str              # "filesystem", "url", "thunderbird", ...
    target: str            # path, url, message-id, etc.
    extra: dict | None = None
