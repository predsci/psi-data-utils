"""Recursively convert PSI HDF4 (.hdf) files in a directory tree to HDF5 (.h5)."""

from __future__ import annotations

import argparse
import shutil
from os import PathLike
from pathlib import Path
from typing import Optional

from psi_io import convert_psih4_to_psih5

HDF5_SUFFIX = '.h5'
HDF4_SUFFIX = '.hdf'


def convert_hdf4_to_hdf5(input_dir: PathLike,
                         output_dir: Optional[PathLike] = None,
                         remove_existing: bool = False) -> None:
    input_dir = Path(input_dir).resolve()
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory {input_dir} does not exist.")
    output_dir = Path(output_dir) if output_dir else input_dir
    equal_io = input_dir == output_dir

    output_dir.mkdir(parents=True, exist_ok=True)
    for path in input_dir.glob('**/*'):
        if path.is_file():
            if path.suffix == HDF4_SUFFIX:
                print(f"Converting {path} to HDF5 ...")
                convert_psih4_to_psih5(path, output_dir / path.relative_to(input_dir).with_suffix(HDF5_SUFFIX))
                if remove_existing:
                    print(f"Removing {path} ...")
                    path.unlink()
            else:
                if not equal_io:
                    print(f"Copying {path.name} to {output_dir / path.relative_to(input_dir)} ...")
                    shutil.copy2(path, output_dir / path.relative_to(input_dir))
        elif path.is_dir() and not equal_io:
            print(f"Creating directory {output_dir / path.relative_to(input_dir)} ...")
            (output_dir / path.relative_to(input_dir)).mkdir(parents=True, exist_ok=True)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "input_dir",
        type=Path,
        help="Directory tree to scan for HDF4 (.hdf) files.",
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        default=None,
        help="Destination for converted files. Defaults to the input directory (convert in place).",
    )
    parser.add_argument(
        "--remove-existing",
        action="store_true",
        help="Delete each source .hdf file after a successful conversion.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> None:
    args = parse_args(argv)
    convert_hdf4_to_hdf5(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        remove_existing=args.remove_existing,
    )


if __name__ == '__main__':
    main()