from __future__ import annotations

import os
import sys


PROJECT_ROOT = os.path.abspath("..")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


project = "Thorlabs Elliptec Motorized Stages"
author = "Pooya Abdolghader"
release = "1.0.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "myst_parser",
]

templates_path = ["_templates"]
exclude_patterns: list[str] = ["_build", "Thumbs.db", ".DS_Store"]

autodoc_member_order = "bysource"
autodoc_typehints = "none"
autodoc_default_options = {
    "inherited-members": True,
}

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_preprocess_types = False

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
