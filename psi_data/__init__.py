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

try:
    from importlib.metadata import version as _pkg_version
    from importlib.metadata import PackageNotFoundError
    from pathlib import Path
    __version__ = _pkg_version("psi-data")  # type: ignore[assignment]
except PackageNotFoundError as e:  # dev/editable without metadata
    try:
        import tomllib  # Python 3.11+
    except ModuleNotFoundError:  # pragma: no cover
        import tomli as tomllib  # pip install tomli

    pyproject = Path(__file__).parents[1].resolve() / 'pyproject.toml'
    data = tomllib.loads(pyproject.read_text())

    project_version = data.get("project", {}).get("version", "0+unknown")
    project_version = project_version.replace('"', '').replace("'", '')
    __version__ = project_version