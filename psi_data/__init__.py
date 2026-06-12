"""Sample data fetching and management utilities for Predictive Science Inc.

This package provides thin, cached download helpers for PSI sample datasets —
MHD model output from MAS and POT3D runs plus standalone example files. Files
are downloaded on demand into a local :mod:`pooch` cache and verified against
packaged checksums, so repeated calls are cheap.

Examples
--------
>>> import psi_data
>>> paths = psi_data.fetch_mas_data(domains="cor", variables="br")  # doctest: +SKIP
>>> paths.cor_br  # doctest: +SKIP
PosixPath('.../cor/mhd/br002.h5')
"""

from ._static_assets import *

__all__ = [*_static_assets.__all__,]

# Hoist the canonical location of the public API from the private implementation
# module up to the package root. This makes documentation tooling (and runtime
# introspection) present these objects as ``psi_data.<name>`` rather than
# ``psi_data._static_assets.<name>``.
for _name in __all__:
    _obj = globals().get(_name)
    if getattr(_obj, "__module__", None) == _static_assets.__name__:
        _obj.__module__ = __name__
del _name, _obj

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from pathlib import Path

# Must match the distribution name (``[project] name``) in pyproject.toml, which
# differs from the import package name ``psi_data``.
try:
    __version__ = _pkg_version("psi-data-utils")  # type: ignore[assignment]
except PackageNotFoundError:  # running from a source tree without install metadata
    __version__ = "0+unknown"
    # pyproject.toml is not shipped inside the installed package, so only read it
    # when it is actually present (i.e. when running from the repository).
    pyproject = Path(__file__).parents[1] / "pyproject.toml"
    if pyproject.is_file():
        try:
            import tomllib  # Python 3.11+
        except ModuleNotFoundError:  # pragma: no cover
            import tomli as tomllib  # Python < 3.11

        data = tomllib.loads(pyproject.read_text())
        __version__ = data.get("project", {}).get("version", "0+unknown")