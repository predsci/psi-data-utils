from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

try:
    # First try to run sphinx_build against installed dist
    # This is primarily included for nox-based doc builds
    import psi_data
except ImportError:
    # Fallback: add project root to sys.path
    # This is included for local dev builds without install
    sys.path.insert(0, Path(__file__).resolve().parents[2].as_posix())
    import psi_data

try:
    from pthree import build_node_tree, node_tree_to_dict
except ImportError:
    raise ImportError(
        "The 'pthree' package is required to build the documentation. "
        "Please install it via 'pip install pthree' and try again."
    )

# ------------------------------------------------------------------------------
# Project Information
# ------------------------------------------------------------------------------
project = "psi-data"
author = "Predictive Science Inc"
copyright = f"{datetime.now():%Y}, {author}"
version = psi_data.__version__
release = psi_data.__version__

# ------------------------------------------------------------------------------
# General Configuration
# ------------------------------------------------------------------------------
extensions = []

# --- HTML Theme
_logo = "https://predsci.com/doc/psi_logo.png"
html_favicon = _logo
html_logo = _logo
html_theme = "sphinx_book_theme"
html_static_path = ["_static"]
html_theme_options = {
    "show_prev_next": False,
    "navigation_with_keys": False,
    "show_nav_level": 3,
    "navigation_depth": 5,
    "logo": {
        "text": f"{project} v{version}",
        "image_light": _logo,
        "image_dark": _logo,
    },
    'icon_links': [
        {
            'name': 'PSI Home',
            'url': 'https://www.predsci.com/',
            'icon': 'fa fa-home fa-fw',
            "type": "fontawesome",
        },
        {
            'name': 'Repository',
            'url': 'https://github.com/predsci/psi-data',
            "icon": "fa-brands fa-github fa-fw",
            "type": "fontawesome",
        },
        {
            'name': 'Documentation',
            'url': 'https://predsci.com/doc/psi-data',
            "icon": "fa fa-file fa-fw",
            "type": "fontawesome",
        },
        {
            'name': 'Contact',
            'url': 'https://www.predsci.com/portal/contact.php',
            'icon': 'fa fa-envelope fa-fw',
            "type": "fontawesome",
        },
    ],
}

# --- Python Syntax
add_module_names = False
python_maximum_signature_line_length = 80

# --- Templating
templates_path = ['_templates', ]

# ------------------------------------------------------------------------------
# Viewcode Configuration
# ------------------------------------------------------------------------------
extensions.append("sphinx.ext.viewcode")

viewcode_line_numbers = True

# ------------------------------------------------------------------------------
# Autosummary Configuration
# ------------------------------------------------------------------------------
extensions.append("sphinx.ext.autosummary")

root_package = 'psi_data'
exclude_private = False
exclude_tests = True
exclude_dunder = True
sort_members = False
exclusions = [
]

node_tree = build_node_tree(root_package,
                            sort_members,
                            exclude_private,
                            exclude_tests,
                            exclude_dunder,
                            exclusions)

autosummary_context = dict(pkgtree=node_tree_to_dict(node_tree))

# ------------------------------------------------------------------------------
# Autodoc Configuration
# ------------------------------------------------------------------------------
extensions.append("sphinx.ext.autodoc")

autodoc_typehints = "none"
autodoc_member_order = 'bysource'
autodoc_default_options = {
    "show-inheritance": True,
}

# ------------------------------------------------------------------------------
# Numpydoc Configuration
# ------------------------------------------------------------------------------
extensions.append("numpydoc")

# numpydoc otherwise auto-injects its own "Methods"/"Attributes" autosummary
# tables into every class, duplicating the tables built by the autosummary
# class.rst template.  Disable it so only the template's tables are rendered.
numpydoc_show_class_members = False

numpydoc_xref_param_type = True
numpydoc_xref_ignore = {"optional", "default", "of", "or"}
numpydoc_xref_aliases = {
    # --- Python standard library ---
    "Path": "pathlib.Path",
    "Callable": "collections.abc.Callable",
    "Sequence": "collections.abc.Sequence",
    "Any": "typing.Any",
    "Literal": "typing.Literal",
}

# ------------------------------------------------------------------------------
# Intersphinx Configuration
# ------------------------------------------------------------------------------
extensions.append("sphinx.ext.intersphinx")

DOCS = Path(__file__).resolve().parents[1]
INV = DOCS / "_intersphinx"
intersphinx_cache_limit = 30
intersphinx_mapping = {
    "python": (
        "https://docs.python.org/3/",
        # (INV / "python-objects.inv").as_posix(),
        None
    ),
    "numpy": (
        "https://numpy.org/doc/stable/",
        # (INV / "numpy-objects.inv").as_posix(),
        None
    ),
    "pooch": (
        "https://www.fatiando.org/pooch/latest/",
        # (INV / "pooch-objects.inv").as_posix(),
        None
    ),
    "h5py": (
        "https://docs.h5py.org/en/stable/",
        # (INV / "h5py-objects.inv").as_posix(),
        None
    ),
    "pyhdf": (
        "https://fhs.github.io/pyhdf/",
        # (INV / "pyhdf-objects.inv").as_posix(),
        None
    ),
    "psi-io": (
        "https://predsci.com/doc/psi-io/",
        # (INV / "psi-io-objects.inv").as_posix(),
        None
    ),
}


# ------------------------------------------------------------------------------
# Sphinx Copy Button Configuration
# ------------------------------------------------------------------------------
extensions.append("sphinx_copybutton")

copybutton_prompt_text = r">>> |\.\.\. "
copybutton_prompt_is_regexp = True

