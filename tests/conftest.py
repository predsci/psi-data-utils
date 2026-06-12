"""Shared pytest fixtures and import-time setup for the psi_data test suite."""

from __future__ import annotations

import os
from pathlib import Path

# psi_data loads its registry at import time, choosing registry.txt normally or
# registry-dev.txt under DEVELOPMENT. Select the mode that matches whichever
# registry file is actually checked in, so the suite imports cleanly either way.
_REGISTRY_DIR = Path(__file__).resolve().parents[1] / "psi_data" / "registry"
if (
    not (_REGISTRY_DIR / "registry.txt").is_file()
    and (_REGISTRY_DIR / "registry-dev.txt").is_file()
):
    os.environ.setdefault("DEVELOPMENT", "1")

import pytest

import psi_data
from psi_data import _static_assets


@pytest.fixture
def fake_fetch(monkeypatch):
    """Replace ``FETCHER.fetch`` with an offline stub that echoes its key.

    The stub records every requested registry key and returns it unchanged, so
    tests can assert on path templating and return shapes without downloading.

    Returns
    -------
    calls : list[str]
        The list, populated as the patched fetcher is called, of registry keys
        requested during the test.
    """
    calls: list[str] = []

    def _fetch(key, progressbar=False):  # noqa: ARG001 - mirror pooch signature
        calls.append(key)
        return key

    monkeypatch.setattr(_static_assets.FETCHER, "fetch", _fetch)
    return calls