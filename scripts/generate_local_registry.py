"""Build a pooch registry text file from a directory tree of asset files."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Optional

import pooch

DEFAULT_REGISTRY_DIR = Path(__file__).parents[1] / "psi_data" / "registry"
DEFAULT_REGISTRY_NAME = "registry-dev.txt"


def generate_local_registry(assets_dir: Path, output: Path) -> None:
    assets_dir = Path(assets_dir).resolve()
    if not assets_dir.exists():
        raise FileNotFoundError(f"Assets directory {assets_dir} does not exist.")

    output = Path(output)
    if not output.parent.exists():
        raise FileNotFoundError(f"Registry output directory {output.parent} does not exist.)")

    print(f"Generating registry for files in {assets_dir} ...")
    pooch.make_registry(str(assets_dir), str(output))
    print(f"Wrote registry to {output}")


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "assets_dir",
        type=Path,
        nargs="?",
        default=os.environ.get("PSI_DATA_DEV_DIR"),
        help="Directory of asset files to hash. Defaults to the $DEV_DIR environment variable.",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=DEFAULT_REGISTRY_DIR / DEFAULT_REGISTRY_NAME,
        help="Path to write the generated registry file.",
    )
    args = parser.parse_args(argv)
    if args.assets_dir is None:
        parser.error("no assets directory given and $DEV_DIR is not set")
    return args


def main(argv: Optional[list[str]] = None) -> None:
    args = parse_args(argv)
    generate_local_registry(assets_dir=args.assets_dir, output=args.output)


if __name__ == '__main__':
    main()