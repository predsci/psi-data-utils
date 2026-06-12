"""Clear the psi-data-utils pooch cache: the default OS cache and any env-var override."""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path
from typing import Optional

import pooch

CACHE_DIR = "psi"
CACHE_ENV = "PSI_DATA_CACHE"


def cache_locations() -> list[Path]:
    """Return the distinct cache directories psi-data-utils may use, in clear order."""
    locations = [Path(pooch.os_cache(CACHE_DIR)).expanduser()]
    env_value = os.environ.get(CACHE_ENV)
    if env_value:
        env_path = Path(env_value).expanduser()
        if env_path not in locations:
            locations.append(env_path)
    return locations


def clear_existing_cache(dry_run: bool = False) -> None:
    for location in cache_locations():
        if not location.exists():
            print(f"Skipping {location} (does not exist).")
            continue
        if dry_run:
            print(f"[dry-run] Would remove {location}")
            continue
        print(f"Removing {location} ...")
        shutil.rmtree(location)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-n", "--dry-run",
        action="store_true",
        help="Show which cache directories would be removed without deleting anything.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> None:
    args = parse_args(argv)
    clear_existing_cache(dry_run=args.dry_run)


if __name__ == "__main__":
    main()