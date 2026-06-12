"""Sample data fetching and management utilities for Predictive Science Inc.

This package provides thin, cached download helpers for PSI sample datasets —
MHD model output from MAS and POT3D runs plus standalone example files. Files
are downloaded on demand into a local :mod:`pooch` cache and verified against
packaged checksums, so repeated calls are cheap.

All public objects are re-exported from :mod:`psi_data._static_assets`:

- :func:`~psi_data._static_assets.fetch_mas_data` — MAS coronal/heliospheric
  MHD fields.
- :func:`~psi_data._static_assets.fetch_mas_quantities` — MAS quantities at the
  inner radial boundary.
- :func:`~psi_data._static_assets.fetch_pot3d_data` — POT3D PFSS magnetic field
  components.
- :func:`~psi_data._static_assets.fetch_example_fieldline`,
  :func:`~psi_data._static_assets.fetch_example_radial_scale`,
  :func:`~psi_data._static_assets.fetch_example_chmapdb` — standalone example
  data files.
- :func:`~psi_data._static_assets.fetch_all` — download the entire registry for
  one HDF version.
- :func:`~psi_data._static_assets.clear_psi_cache` — remove the local download
  cache.
- :class:`~psi_data._static_assets.RegistryWarning` — warning for unavailable
  registry files.

Examples
--------
>>> import psi_data
>>> paths = psi_data.fetch_mas_data(domains="cor", variables="br")  # doctest: +SKIP
>>> paths.cor_br  # doctest: +SKIP
PosixPath('.../cor/mhd/br002.h5')

Attributes
----------
__version__ : str
    Installed package version, resolved from package metadata or, in an
    editable checkout without metadata, from ``pyproject.toml``.
"""

from ._static_assets import *

__all__ = [*_static_assets.__all__,]

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