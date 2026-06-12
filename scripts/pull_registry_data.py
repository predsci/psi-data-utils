"""Pull every file in the shipped PSI registry into the local dev assets directory.

Downloads each entry of the packaged ``registry.txt`` from the published PSI
asset host into ``$PSI_DATA_DEV_DIR``, preserving the registry-relative
directory tree and verifying each file against its recorded checksum. This
mirrors the published assets locally so that the development server
(``run_development_server.py``) can serve them.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Optional

import pooch

# Production asset host and the registry shipped with the package. Defined here
# (rather than imported from psi_data) so this script is unaffected by the
# DEVELOPMENT environment toggle, which repoints the package's BASE_URL and
# registry to the local development server.
PROD_BASE_URL = "https://www.predsci.com/doc/assets/"
DEFAULT_REGISTRY = Path(__file__).parents[1] / "psi_data" / "registry" / "registry.txt"


def _is_hidden(key: str) -> bool:
    """Return True if any path component of registry key *key* starts with a dot."""
    return any(part.startswith(".") for part in Path(key).parts)


def pull_registry_data(dev_dir: Path,
                       registry: Path = DEFAULT_REGISTRY,
                       base_url: str = PROD_BASE_URL,
                       include_hidden: bool = False) -> list[Path]:
    """Download every registered file into *dev_dir*, preserving the tree.

    Parameters
    ----------
    dev_dir : Path
        Destination directory. Files are written under their registry-relative
        paths; created if it does not exist.
    registry : Path, optional
        Registry file listing the keys and checksums to pull. Default is the
        ``registry.txt`` shipped with the package.
    base_url : str, optional
        Root URL to download from. Default is the published PSI asset host.
    include_hidden : bool, optional
        If False (default), skip registry keys with hidden path components
        (e.g. ``.DS_Store``).

    Returns
    -------
    paths : list[Path]
        Local paths of the downloaded files.

    Raises
    ------
    FileNotFoundError
        If *registry* does not exist.
    """
    dev_dir = Path(dev_dir).resolve()
    dev_dir.mkdir(parents=True, exist_ok=True)

    registry = Path(registry)
    if not registry.is_file():
        raise FileNotFoundError(f"Registry file {registry} does not exist.")

    fetcher = pooch.create(path=dev_dir, base_url=base_url, registry=None)
    fetcher.load_registry(str(registry))

    keys = list(fetcher.registry)
    selected = [k for k in keys if include_hidden or not _is_hidden(k)]
    skipped = len(keys) - len(selected)

    print(f"Pulling {len(selected)} file(s) from {base_url} into {dev_dir} ...")
    if skipped:
        print(f"Skipping {skipped} hidden registry entries.")

    paths = [Path(fetcher.fetch(key, progressbar=True)) for key in selected]
    print(f"Done. {len(paths)} file(s) available under {dev_dir}.")
    return paths


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "dev_dir",
        type=Path,
        nargs="?",
        default=os.environ.get("PSI_DATA_DEV_DIR"),
        help="Destination directory. Defaults to the $PSI_DATA_DEV_DIR environment variable.",
    )
    parser.add_argument(
        "-r", "--registry",
        type=Path,
        default=DEFAULT_REGISTRY,
        help="Registry file listing the files to pull.",
    )
    parser.add_argument(
        "-b", "--base-url",
        default=PROD_BASE_URL,
        help="Root URL to download data files from.",
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Also pull registry entries with hidden path components (e.g. .DS_Store).",
    )
    args = parser.parse_args(argv)
    if args.dev_dir is None:
        parser.error("no destination directory given and $PSI_DATA_DEV_DIR is not set")
    return args


def main(argv: Optional[list[str]] = None) -> None:
    args = parse_args(argv)
    pull_registry_data(
        dev_dir=args.dev_dir,
        registry=args.registry,
        base_url=args.base_url,
        include_hidden=args.include_hidden,
    )


if __name__ == "__main__":
    main()