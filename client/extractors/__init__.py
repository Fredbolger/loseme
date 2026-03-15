from .registry import extractor_registry

# Import all extractors to trigger self-registration
from . import pdf_extractor
from . import plaintext_extractor
from . import python_extractor
from . import html_extractor
from . import eml_extractor
from . import thunderbird_extractor
