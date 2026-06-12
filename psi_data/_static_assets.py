"""Download and cache PSI sample datasets via :mod:`pooch`.

This module backs the public :mod:`psi_data` API. It configures a single
module-level fetcher (:data:`FETCHER`) against a registry of MHD model outputs
and example data files, and exposes ``fetch_*`` helpers that download the
requested files on demand and return their on-disk paths.

The bundled data come from a thermodynamic MAS standard run for Carrington
rotation 2309 driven by an HMI magnetogram, spanning the coronal (``cor``) and
heliospheric (``hel``) domains, together with a POT3D potential-field solution
and a handful of standalone example files. Files are fetched into the
:mod:`pooch` OS cache (overridable through the :envvar:`PSI_DATA_CACHE`
environment variable) and verified against the packaged registry hashes, so
repeated calls are cheap.

Setting the :envvar:`DEVELOPMENT` environment variable redirects the fetcher to
a local development server (``http://localhost:8000``) and selects the
development registry instead of the published PSI asset host.

See Also
--------
pooch.Pooch : The underlying download-and-cache manager.
clear_psi_cache : Remove cached files written by the fetchers.

Examples
--------
>>> from psi_data import fetch_mas_data
>>> paths = fetch_mas_data(domains="cor", variables="br")  # doctest: +SKIP
>>> paths.cor_br  # doctest: +SKIP
PosixPath('.../H5CR2309_hmi_mast_mas_std_0201/cor/mhd/br002.h5')
"""

from __future__ import annotations

import os
import shutil
import warnings
from collections import namedtuple
from collections.abc import Callable
from functools import partial, wraps
from itertools import product
from types import MappingProxyType
from typing import Iterable, Optional

import pooch
from importlib.resources import as_file, files
from pathlib import Path

__all__ = [
    "fetch_mas_data",
    "fetch_mas_quantities",
    "fetch_pot3d_data",
    "fetch_example_fieldline",
    "fetch_example_radial_scale",
    "fetch_example_chmapdb",
    "clear_psi_cache",
    "fetch_all",
    "RegistryWarning",
]

class RegistryWarning(UserWarning):
    """Warning emitted when a requested data file is unavailable.

    Notes
    -----
    Raised in place of an error by ``fetch_*`` helpers when an optional file is
    absent from the registry for the requested HDF version, allowing callers to
    continue. See :func:`fetch_example_chmapdb`.
    """


Filepaths = partial(namedtuple, "Filepaths")
"""Factory that builds a ``Filepaths`` named-tuple class from field names."""

HDF_EXT = MappingProxyType({
    4: ".hdf",
    5: ".h5",
})
"""Mapping of supported HDF format version (``4``, ``5``) to file extension."""

DOM_VAR_MAP = MappingProxyType({
    "cor": {"br", "bt", "bp", "vr", "vt", "vp", "jr", "jt", "jp", "t", "rho", "p", "ep", "em", "zp", "zm", "heat"}, # "te", "tp",
    "hel": {"br", "bt", "bp", "vr", "vt", "vp", "jr", "jt", "jp", "t", "rho", "p"},
    "pot3d": {"br", "bt", "bp"},
    "quantities": {"ch_pm",}
})
"""Mapping of each model domain to the set of variable names it provides."""

REGISTRY_DIR = "registry"
"""Package subdirectory containing the bundled registry file(s)."""

REGISTRY_FILE = "registry.txt"
"""Name of the active registry file; development builds use ``registry-dev.txt``."""

BASE_URL = "https://www.predsci.com/doc/assets/"
"""Root URL the fetcher downloads data files from."""

CACHE_DIR = "psi"
""":mod:`pooch` OS-cache project name under which downloaded files are stored."""

CACHE_ENV = "PSI_DATA_CACHE"
"""Environment variable that, when set, overrides the on-disk cache location."""

if os.environ.get("DEVELOPMENT"):
    host, port = "localhost", 8000

    REGISTRY_FILE = "registry-dev.txt"
    BASE_URL = f"http://{host}:{port}"


FETCHER = pooch.create(
    path=pooch.os_cache(CACHE_DIR),
    base_url=BASE_URL,
    registry=None,
    env=CACHE_ENV,
)
"""Module-level :class:`pooch.Pooch` manager that downloads and caches PSI data files."""


registry_resource = files("psi_data").joinpath(REGISTRY_DIR, REGISTRY_FILE)
with as_file(registry_resource) as registry_path:
    if not registry_path.is_file():
        raise FileNotFoundError(
            f"Registry file {REGISTRY_FILE!r} not found in package data. "
            "Ensure it has been generated and shipped with the package.",
        )
    FETCHER.load_registry(registry_path)


def _check_hdf_version(func) -> Callable:
    """Wrap a fetcher to validate its ``hdf`` keyword argument.

    Parameters
    ----------
    func : Callable
        A fetcher that accepts an ``hdf`` keyword argument.

    Returns
    -------
    wrapper : Callable
        The wrapped fetcher, which raises :exc:`ValueError` for unsupported
        HDF versions before delegating to *func*.
    """
    @wraps(func)
    def wrapper(*args, hdf: int = 5, **kwargs):
        """Validate *hdf* against :data:`HDF_EXT`, then call the wrapped fetcher."""
        if hdf not in HDF_EXT:
            raise ValueError(f"Unsupported HDF version: {hdf}. "
                             f"Supported versions are: {list(HDF_EXT.keys())}")
        return func(*args, hdf=hdf, **kwargs)
    return wrapper


@_check_hdf_version
def fetch_mas_data(*, domains: Optional[Iterable] = 'cor',
                   variables: Optional[Iterable] = 'br',
                   hdf: int = 5) -> object:
    r"""Fetch MAS magnetohydrodynamic model output for the given domains and variables.

    Downloads the requested MAS field files from the Carrington rotation 2309
    standard run and returns their cached paths. One file is fetched for each
    requested ``(domain, variable)`` pair.

    Parameters
    ----------
    domains : str | Iterable | None, optional
        Model domain(s) to fetch: ``"cor"`` (corona) and/or ``"hel"``
        (heliosphere). Accepts a comma-separated string, an iterable of domain
        names, or ``None`` to fetch both domains. Default is ``"cor"``.
    variables : str | Iterable | None, optional
        Physical variable(s) to fetch, such as the magnetic field components
        ``"br"``, ``"bt"``, ``"bp"`` (:math:`\mathbf{B}`) or the velocity
        components ``"vr"``, ``"vt"``, ``"vp"`` (:math:`\mathbf{v}`). Accepts a
        comma-separated string, an iterable of variable names, or ``None`` to
        fetch every variable common to all requested domains. Default is
        ``"br"``.
    hdf : int, optional
        HDF format version to download: ``4`` (``.hdf``) or ``5`` (``.h5``).
        Default is ``5``.

    Returns
    -------
    paths : Filepaths
        Named tuple whose fields are ``"{domain}_{variable}"`` and whose values
        are the :class:`~pathlib.Path` of each downloaded file.

    Raises
    ------
    ValueError
        If *hdf* is not a supported HDF version.
    KeyError
        If *variables* is ``None`` and a requested domain is not present in
        :data:`DOM_VAR_MAP`.

    See Also
    --------
    fetch_pot3d_data : Fetch POT3D potential-field components.
    fetch_mas_quantities : Fetch derived MAS quantities at the inner boundary.

    Examples
    --------
    >>> from psi_data import fetch_mas_data
    >>> paths = fetch_mas_data(domains="cor,hel", variables="br,vr")  # doctest: +SKIP
    >>> paths.cor_br  # doctest: +SKIP
    PosixPath('.../cor/mhd/br002.h5')
    """
    if domains is None:
        domains = {"cor", "hel"}
    else:
        domains = set(domains.replace(" ", "").lower().split(",") if isinstance(domains, str) else domains)

    if variables is None:
        variables = set.intersection(*(DOM_VAR_MAP[dom] for dom in domains))
    else:
        variables = set(variables.replace(" ", "").lower().split(",") if isinstance(variables, str) else variables)
    req_pairs = product(domains, variables)

    ext = HDF_EXT.get(hdf)
    filepaths = {
        f"{dom}_{var}":
            Path(
                FETCHER.fetch(
                    f"H{hdf}CR2309_hmi_mast_mas_std_0201/{dom}/mhd/{var}002{ext}",
                    progressbar=True))
        for dom, var in req_pairs
    }

    return Filepaths(filepaths.keys())(*filepaths.values())


@_check_hdf_version
def fetch_mas_quantities(*, quantities: Optional[Iterable] = 'ch_pm', hdf: int = 5) -> object:
    r"""Fetch derived MAS quantities defined at the model inner radial boundary.

    Downloads MAS "quantities at :math:`r_0`" files — scalar quantities
    evaluated at the inner radial boundary of the coronal domain — and returns
    their cached paths.

    Parameters
    ----------
    quantities : str | Iterable | None, optional
        Quantity name(s) to fetch, e.g. ``"ch_pm"``. Accepts a comma-separated
        string, an iterable of quantity names, or ``None`` to fetch every
        available quantity. Default is ``"ch_pm"``.
    hdf : int, optional
        HDF format version to download: ``4`` (``.hdf``) or ``5`` (``.h5``).
        Default is ``5``.

    Returns
    -------
    paths : Filepaths
        Named tuple whose fields are the quantity names and whose values are
        the :class:`~pathlib.Path` of each downloaded file.

    Raises
    ------
    ValueError
        If *hdf* is not a supported HDF version.

    See Also
    --------
    fetch_mas_data : Fetch full MAS MHD field output.

    Examples
    --------
    >>> from psi_data import fetch_mas_quantities
    >>> paths = fetch_mas_quantities(quantities="ch_pm")  # doctest: +SKIP
    >>> paths.ch_pm  # doctest: +SKIP
    PosixPath('.../cor/quantities_at_r0/ch_pm.h5')
    """
    if quantities is None:
        quantities = DOM_VAR_MAP["quantities"]
    else:
        quantities = set(quantities.replace(" ", "").lower().split(",") if isinstance(quantities, str) else quantities)

    ext = HDF_EXT.get(hdf)
    filepaths = {
        f"{var}":
            Path(
                FETCHER.fetch(
                    f"H{hdf}CR2309_hmi_mast_mas_std_0201/cor/quantities_at_r0/{var}{ext}",
                    progressbar=True))
        for var in quantities
    }

    return Filepaths(filepaths.keys())(*filepaths.values())


@_check_hdf_version
def fetch_pot3d_data(*, variables: Optional[Iterable] = 'br', hdf: int = 5) -> object:
    r"""Fetch POT3D potential-field source-surface (PFSS) magnetic field components.

    Downloads the POT3D PFSS solution components for the coronal domain and
    returns their cached paths.

    Parameters
    ----------
    variables : str | Iterable | None, optional
        Magnetic field component(s) to fetch: ``"br"``, ``"bt"``, ``"bp"``
        (:math:`\mathbf{B}`). Accepts a comma-separated string, an iterable of
        component names, or ``None`` to fetch all three components. Default is
        ``"br"``.
    hdf : int, optional
        HDF format version to download: ``4`` (``.hdf``) or ``5`` (``.h5``).
        Default is ``5``.

    Returns
    -------
    paths : Filepaths
        Named tuple whose fields are the component names and whose values are
        the :class:`~pathlib.Path` of each downloaded file.

    Raises
    ------
    ValueError
        If *hdf* is not a supported HDF version.

    See Also
    --------
    fetch_mas_data : Fetch full MAS MHD field output.

    Examples
    --------
    >>> from psi_data import fetch_pot3d_data
    >>> paths = fetch_pot3d_data(variables="br,bt,bp")  # doctest: +SKIP
    >>> paths.br  # doctest: +SKIP
    PosixPath('.../cor/pfss/br.h5')
    """
    if variables is None:
        variables = DOM_VAR_MAP["pot3d"]
    else:
        variables = set(variables.replace(" ", "").lower().split(",") if isinstance(variables, str) else variables)

    ext = HDF_EXT.get(hdf)
    filepaths = {
        f"{var}":
            Path(
                FETCHER.fetch(
                    f"H{hdf}CR2309_hmi_mast_mas_std_0201/cor/pfss/{var}{ext}",
                    progressbar=True))
        for var in variables
    }

    return Filepaths(filepaths.keys())(*filepaths.values())


@_check_hdf_version
def fetch_example_fieldline(*, hdf: int = 5) -> Path:
    """Fetch the bundled example magnetic field line trace data file.

    Parameters
    ----------
    hdf : int, optional
        HDF format version to download: ``4`` (``.hdf``) or ``5`` (``.h5``).
        Default is ``5``.

    Returns
    -------
    path : Path
        Cached path of the downloaded field line example file.

    Raises
    ------
    ValueError
        If *hdf* is not a supported HDF version.

    See Also
    --------
    fetch_example_radial_scale : Fetch the example radial scaling data file.
    fetch_example_chmapdb : Fetch the example coronal-hole map database.

    Examples
    --------
    >>> from psi_data import fetch_example_fieldline
    >>> path = fetch_example_fieldline()  # doctest: +SKIP
    >>> path.name  # doctest: +SKIP
    'fieldline.h5'
    """
    ext = HDF_EXT.get(hdf)
    return Path(
        FETCHER.fetch(
            f"example_datafiles/fieldline{ext}",
            progressbar=True))


@_check_hdf_version
def fetch_example_radial_scale(*, hdf: int = 5) -> Path:
    r"""Fetch the bundled example radial scaling data file.

    Parameters
    ----------
    hdf : int, optional
        HDF format version to download: ``4`` (``.hdf``) or ``5`` (``.h5``).
        Default is ``5``.

    Returns
    -------
    path : Path
        Cached path of the downloaded radial scaling example file.

    Raises
    ------
    ValueError
        If *hdf* is not a supported HDF version.

    See Also
    --------
    fetch_example_fieldline : Fetch the example field line data file.

    Notes
    -----
    The radial scaling profile is commonly used to rescale MHD variables that
    fall off steeply with heliocentric radius :math:`r`, improving the dynamic
    range of visualizations.

    Examples
    --------
    >>> from psi_data import fetch_example_radial_scale
    >>> path = fetch_example_radial_scale()  # doctest: +SKIP
    >>> path.name  # doctest: +SKIP
    'rscale.h5'
    """
    ext = HDF_EXT.get(hdf)
    return Path(
        FETCHER.fetch(
            f"example_datafiles/rscale{ext}",
            progressbar=True))


@_check_hdf_version
def fetch_example_chmapdb(*, hdf: int = 5) -> Path | None:
    """Fetch the bundled example coronal-hole map database, if available.

    Parameters
    ----------
    hdf : int, optional
        HDF format version to download: ``4`` (``.hdf``) or ``5`` (``.h5``).
        Default is ``5``.

    Returns
    -------
    path : Path | None
        Cached path of the downloaded coronal-hole map database, or ``None`` if
        the file is unavailable for the requested HDF version.

    Raises
    ------
    ValueError
        If *hdf* is not a supported HDF version.

    Warns
    -----
    RegistryWarning
        If the database is not available for the requested HDF version (it is
        currently provided only for HDF5).

    See Also
    --------
    fetch_example_fieldline : Fetch the example field line data file.

    Examples
    --------
    >>> from psi_data import fetch_example_chmapdb
    >>> path = fetch_example_chmapdb(hdf=5)  # doctest: +SKIP
    >>> path.name  # doctest: +SKIP
    'chmap.h5'
    """
    ext = HDF_EXT.get(hdf)

    try:
        return Path(
            FETCHER.fetch(
                f"example_datafiles/chmap{ext}",
                progressbar=True))
    except ValueError:
        warnings.warn(
            f"Example CHMAP database file not found for HDF version {hdf}. "
            "This file is only available for HDF5. Returning None.",
            RegistryWarning,
        )
        return None


@_check_hdf_version
def fetch_all(*, hdf: int = 5) -> list[Path]:
    """Fetch every registry file matching the requested HDF version.

    Downloads all files in the fetcher registry whose names end with the
    extension for the requested HDF version and returns their cached paths.

    Parameters
    ----------
    hdf : int, optional
        HDF format version to download: ``4`` (``.hdf``) or ``5`` (``.h5``).
        Default is ``5``.

    Returns
    -------
    filepaths : list[Path]
        Cached paths of every downloaded file, in registry order.

    Raises
    ------
    ValueError
        If *hdf* is not a supported HDF version.

    Notes
    -----
    This downloads the entire data collection for the chosen format and may
    transfer a large volume of data on its first invocation.

    See Also
    --------
    fetch_mas_data : Fetch a targeted subset of MAS field output.

    Examples
    --------
    >>> from psi_data import fetch_all
    >>> paths = fetch_all(hdf=5)  # doctest: +SKIP
    >>> all(p.suffix == ".h5" for p in paths)  # doctest: +SKIP
    True
    """
    ext = HDF_EXT.get(hdf)
    keys = FETCHER.registry.keys()
    filtered_paths = filter(lambda k: k.endswith(ext), keys)
    filepaths = [Path(FETCHER.fetch(k, progressbar=True)) for k in filtered_paths]
    return filepaths



def _cache_locations() -> list[Path]:
    """Return the distinct cache directories psi_data may write to.

    Returns
    -------
    locations : list[Path]
        The default :mod:`pooch` OS cache directory, followed by the
        :envvar:`PSI_DATA_CACHE` override when it is set and distinct.
    """
    locations = [Path(pooch.os_cache(CACHE_DIR)).expanduser()]
    env_value = os.environ.get(CACHE_ENV)
    if env_value:
        env_path = Path(env_value).expanduser()
        if env_path not in locations:
            locations.append(env_path)
    return locations


def clear_psi_cache(dry_run: bool = True, prompt: bool = True):
    """Delete cached data files downloaded by the ``fetch_*`` helpers.

    Removes the :mod:`pooch` cache directories used by :data:`FETCHER` — the
    default OS cache and the :envvar:`PSI_DATA_CACHE` override when set.
    Directories that do not exist are skipped.

    Parameters
    ----------
    dry_run : bool, optional
        If ``True``, only report which directories would be removed without
        deleting anything. Default is ``True``.
    prompt : bool, optional
        If ``True``, ask for interactive confirmation before removing each
        directory. Ignored when *dry_run* is ``True``. Default is ``True``.

    See Also
    --------
    pooch.os_cache : Resolves the platform-specific cache directory.

    Examples
    --------
    >>> from psi_data import clear_psi_cache
    >>> clear_psi_cache(dry_run=True)  # doctest: +SKIP
    [dry-run] Would remove cache directory: ...
    """
    for location in _cache_locations():
        if not location.exists():
            print(f"Skipping {location} (does not exist).")
            continue
        if dry_run:
            print(f"[dry-run] Would remove cache directory: {location}")
            continue

        print(f"Removing cache directory: {location}")
        answer = input("Continue? [y/n]: ").strip().lower() in {"y", "yes"} if prompt else True

        if answer:
            shutil.rmtree(location)
        else:
            print("Aborting cache clear.")
