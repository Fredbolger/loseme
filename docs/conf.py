# LoseMe Documentation Configuration
import os
import sys

# Add project root to path
ROOT = os.path.abspath(os.path.join(__file__, "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "core"))
sys.path.insert(0, os.path.join(ROOT, "server"))
sys.path.insert(0, os.path.join(ROOT, "client"))

# -- Project information -----------------------------------------------------
project = "LoseMe"
author = "Benjamin Vyllen"
release = "0.1.0"

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.autosummary",
    "myst_parser",
]

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True

# Autosummary settings
autosummary_generate = True
autodoc_member_order = "bysource"
autodoc_typehints = "description"

# -- Options for HTML output -------------------------------------------------
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

# Theme options
html_theme_options = {
    "navigation_depth": 4,
    "collapse_navigation": False,
}

# Don't include module indices
autosummary_import = lambda name: None

# Exclude patterns
exclude_patterns = ["_build", "**/__pycache__", "*.md"]

# Master document
root_doc = "index"

# Suppress warnings
suppress_warnings = ["autosectionlabel.*"]

