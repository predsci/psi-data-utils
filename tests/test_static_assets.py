"""Basic functionality tests for :mod:`psi_data._static_assets`.

These tests exercise the package's offline behavior: public API surface,
constant tables, argument normalization, registry-key templating, HDF version
validation, the unavailable-file warning path, and cache clearing. Network
downloads are avoided by patching ``FETCHER.fetch`` (see the ``fake_fetch``
fixture in ``conftest.py``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

import psi_data
from psi_data import _static_assets as sa


# --- Public API and metadata -------------------------------------------------

def test_version_is_nonempty_string():
    assert isinstance(psi_data.__version__, str)
    assert psi_data.__version__


def test_public_api_is_importable():
    for name in psi_data.__all__:
        assert hasattr(psi_data, name), f"missing public export: {name}"


# --- Constant tables ---------------------------------------------------------

def test_hdf_ext_mapping():
    assert sa.HDF_EXT[4] == ".hdf"
    assert sa.HDF_EXT[5] == ".h5"


def test_dom_var_map_structure():
    assert {"cor", "hel", "pot3d", "quantities"} <= set(sa.DOM_VAR_MAP)
    assert {"br", "bt", "bp"} <= sa.DOM_VAR_MAP["cor"]
    assert sa.DOM_VAR_MAP["pot3d"] == {"br", "bt", "bp"}
    assert sa.DOM_VAR_MAP["quantities"] == {"ch_pm"}


def test_registry_loaded():
    assert len(sa.FETCHER.registry) > 0


# --- HDF version validation --------------------------------------------------

@pytest.mark.parametrize(
    "fetcher",
    [
        sa.fetch_mas_data,
        sa.fetch_mas_quantities,
        sa.fetch_pot3d_data,
        sa.fetch_example_fieldline,
        sa.fetch_example_radial_scale,
        sa.fetch_example_chmapdb,
        sa.fetch_all,
    ],
)
def test_unsupported_hdf_version_raises(fetcher):
    # The version check runs before any download, so no network access occurs.
    with pytest.raises(ValueError, match="Unsupported HDF version"):
        fetcher(hdf=3)


# --- fetch_mas_data ----------------------------------------------------------

def test_fetch_mas_data_single_pair(fake_fetch):
    paths = sa.fetch_mas_data(domains="cor", variables="br", hdf=5)
    assert paths._fields == ("cor_br",)
    assert paths.cor_br == Path("H5CR2309_hmi_mast_mas_std_0201/cor/mhd/br002.h5")
    assert fake_fetch == ["H5CR2309_hmi_mast_mas_std_0201/cor/mhd/br002.h5"]


def test_fetch_mas_data_comma_string_and_whitespace(fake_fetch):
    paths = sa.fetch_mas_data(domains="cor, hel", variables="br, vr", hdf=5)
    assert set(paths._fields) == {"cor_br", "cor_vr", "hel_br", "hel_vr"}
    assert len(fake_fetch) == 4


def test_fetch_mas_data_iterable_input(fake_fetch):
    paths = sa.fetch_mas_data(domains=["cor"], variables=["br", "bt"], hdf=5)
    assert set(paths._fields) == {"cor_br", "cor_bt"}


def test_fetch_mas_data_domains_none_uses_both(fake_fetch):
    paths = sa.fetch_mas_data(domains=None, variables="br", hdf=5)
    assert set(paths._fields) == {"cor_br", "hel_br"}


def test_fetch_mas_data_variables_none_uses_intersection(fake_fetch):
    paths = sa.fetch_mas_data(domains="cor,hel", variables=None, hdf=5)
    expected_vars = sa.DOM_VAR_MAP["cor"] & sa.DOM_VAR_MAP["hel"]
    fetched_vars = {field.split("_", 1)[1] for field in paths._fields}
    assert fetched_vars == expected_vars


def test_fetch_mas_data_keys_exist_in_registry(fake_fetch):
    # Confirm the templated keys match real registry entries (HDF4 set).
    sa.fetch_mas_data(domains="cor", variables="br,bt,bp", hdf=4)
    for key in fake_fetch:
        assert key in sa.FETCHER.registry, f"{key} not in registry"


# --- fetch_pot3d_data --------------------------------------------------------

def test_fetch_pot3d_data_default(fake_fetch):
    paths = sa.fetch_pot3d_data(variables="br", hdf=5)
    assert paths._fields == ("br",)
    assert paths.br == Path("H5CR2309_hmi_mast_mas_std_0201/cor/pfss/br.h5")


def test_fetch_pot3d_data_none_fetches_all_components(fake_fetch):
    paths = sa.fetch_pot3d_data(variables=None, hdf=5)
    assert set(paths._fields) == {"br", "bt", "bp"}


# --- fetch_mas_quantities ----------------------------------------------------

def test_fetch_mas_quantities_default(fake_fetch):
    paths = sa.fetch_mas_quantities(quantities="ch_pm", hdf=5)
    assert paths._fields == ("ch_pm",)
    assert paths.ch_pm == Path(
        "H5CR2309_hmi_mast_mas_std_0201/cor/quantities_at_r0/ch_pm.h5"
    )


# --- example fetchers --------------------------------------------------------

def test_fetch_example_fieldline(fake_fetch):
    path = sa.fetch_example_fieldline(hdf=5)
    assert path == Path("example_datafiles/fieldline.h5")


def test_fetch_example_radial_scale(fake_fetch):
    path = sa.fetch_example_radial_scale(hdf=4)
    assert path == Path("example_datafiles/rscale.hdf")


def test_fetch_example_chmapdb_warns_and_returns_none(monkeypatch):
    def _raise(key, progressbar=False):  # noqa: ARG001
        raise ValueError("file not in registry")

    monkeypatch.setattr(sa.FETCHER, "fetch", _raise)
    with pytest.warns(sa.RegistryWarning):
        result = sa.fetch_example_chmapdb(hdf=4)
    assert result is None


# --- fetch_all ---------------------------------------------------------------

def test_fetch_all_filters_by_extension(fake_fetch):
    paths = sa.fetch_all(hdf=5)
    assert paths, "expected at least one .h5 entry in the dev registry"
    assert all(p.suffix == ".h5" for p in paths)
    expected = [k for k in sa.FETCHER.registry if k.endswith(".h5")]
    assert len(paths) == len(expected)


# --- clear_psi_cache ---------------------------------------------------------

def test_clear_psi_cache_dry_run_keeps_files(monkeypatch, tmp_path, capsys):
    # Point the default OS cache at a nonexistent dir so only the env cache is real.
    monkeypatch.setattr(sa.pooch, "os_cache", lambda name: tmp_path / "default")
    cache = tmp_path / "env_cache"
    cache.mkdir()
    monkeypatch.setenv(sa.CACHE_ENV, str(cache))

    sa.clear_psi_cache(dry_run=True)

    assert cache.exists()
    assert "dry-run" in capsys.readouterr().out


def test_clear_psi_cache_removes_files(monkeypatch, tmp_path):
    monkeypatch.setattr(sa.pooch, "os_cache", lambda name: tmp_path / "default")
    cache = tmp_path / "env_cache"
    cache.mkdir()
    (cache / "data.h5").write_text("stub")
    monkeypatch.setenv(sa.CACHE_ENV, str(cache))

    sa.clear_psi_cache(dry_run=False, prompt=False)

    assert not cache.exists()


def test_cache_locations_includes_env_override(monkeypatch, tmp_path):
    monkeypatch.setattr(sa.pooch, "os_cache", lambda name: tmp_path / "default")
    monkeypatch.setenv(sa.CACHE_ENV, str(tmp_path / "override"))
    locations = sa._cache_locations()
    assert (tmp_path / "default") in locations
    assert (tmp_path / "override") in locations