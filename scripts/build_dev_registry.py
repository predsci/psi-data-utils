"""Clean the dev assets dir, regenerate registry-dev.txt, and verify it against the shipped registry.

Intended to run after ``pull_registry_data.py``. It removes hidden files and
directories (dot-prefixed, e.g. ``.DS_Store``) from ``$PSI_DATA_DEV_DIR``,
regenerates ``registry-dev.txt`` from the cleaned tree, then verifies the result
against the packaged ``registry.txt`` so that the development registry stays
consistent with the published one.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path, PurePosixPath
from typing import Optional

import pooch

DEFAULT_REGISTRY_DIR = Path(__file__).parents[1] / "psi_data" / "registry"
DEV_REGISTRY = DEFAULT_REGISTRY_DIR / "registry-dev.txt"
PROD_REGISTRY = DEFAULT_REGISTRY_DIR / "registry.txt"


def _key_hidden(key: str) -> bool:
    """Return True if any component of a registry key starts with a dot."""
    return any(part.startswith(".") for part in PurePosixPath(key).parts)


def clean_hidden(dev_dir: Path, dry_run: bool = False) -> list[Path]:
    """Remove hidden files and directories from *dev_dir*.

    Parameters
    ----------
    dev_dir : Path
        Directory tree to clean.
    dry_run : bool, optional
        If True, report what would be removed without deleting anything.
        Default is False.

    Returns
    -------
    removed : list[Path]
        The hidden paths that were (or, under *dry_run*, would be) removed.
    """
    removed: list[Path] = []
    for path in sorted(dev_dir.rglob("*")):
        if not path.exists():  # a parent hidden dir was already removed
            continue
        rel = path.relative_to(dev_dir)
        if not any(part.startswith(".") for part in rel.parts):
            continue
        removed.append(path)
        if dry_run:
            continue
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)
    return removed


def parse_registry(path: Path) -> dict[str, str]:
    """Parse a pooch registry file into a ``{key: hash}`` mapping.

    Parameters
    ----------
    path : Path
        Registry file in pooch's ``"<relative-path> <hash>"`` line format.

    Returns
    -------
    entries : dict[str, str]
        Mapping of each registry key to its checksum string.
    """
    entries: dict[str, str] = {}
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, hashval = line.rsplit(maxsplit=1)
        entries[key] = hashval
    return entries


def verify_against(dev_reg: dict[str, str],
                   reference_reg: dict[str, str],
                   ignore_hidden: bool = True) -> bool:
    """Compare a generated registry against a reference, reporting differences.

    Parameters
    ----------
    dev_reg : dict[str, str]
        The freshly generated development registry mapping.
    reference_reg : dict[str, str]
        The reference (shipped) registry mapping to verify against.
    ignore_hidden : bool, optional
        If True (default), drop hidden keys from both sides before comparing.

    Returns
    -------
    ok : bool
        True when the key sets and all shared checksums match.
    """
    if ignore_hidden:
        dev_reg = {k: v for k, v in dev_reg.items() if not _key_hidden(k)}
        reference_reg = {k: v for k, v in reference_reg.items() if not _key_hidden(k)}

    dev_keys, ref_keys = set(dev_reg), set(reference_reg)
    missing = sorted(ref_keys - dev_keys)
    extra = sorted(dev_keys - ref_keys)
    mismatched = sorted(k for k in dev_keys & ref_keys if dev_reg[k] != reference_reg[k])

    for key in missing:
        print(f"  MISSING  (in shipped registry, absent locally): {key}")
    for key in extra:
        print(f"  EXTRA    (local only, not in shipped registry): {key}")
    for key in mismatched:
        print(f"  MISMATCH (checksum differs): {key}")

    ok = not (missing or extra or mismatched)
    if ok:
        print(f"Verification passed: {len(dev_keys)} entries match the shipped registry.")
    else:
        print(
            f"Verification FAILED: {len(missing)} missing, "
            f"{len(extra)} extra, {len(mismatched)} mismatched.",
        )
    return ok


def build_dev_registry(dev_dir: Path,
                       output: Path = DEV_REGISTRY,
                       reference: Path = PROD_REGISTRY,
                       keep_hidden: bool = False,
                       verify: bool = True,
                       dry_run: bool = False) -> bool:
    """Clean *dev_dir*, regenerate the dev registry, and verify it.

    Parameters
    ----------
    dev_dir : Path
        Directory of pulled asset files.
    output : Path, optional
        Path to write the generated development registry. Default is the
        packaged ``registry-dev.txt``.
    reference : Path, optional
        Shipped registry to verify against. Default is the packaged
        ``registry.txt``.
    keep_hidden : bool, optional
        If True, skip removing hidden files/directories. Default is False.
    verify : bool, optional
        If True (default), verify the generated registry against *reference*.
    dry_run : bool, optional
        If True, only report the hidden files that would be removed, then stop
        without generating or verifying. Default is False.

    Returns
    -------
    ok : bool
        True if the registry was generated and (when requested) verification
        passed. Always True for a *dry_run*.

    Raises
    ------
    FileNotFoundError
        If *dev_dir* does not exist, or *reference* is missing when verifying.
    """
    dev_dir = Path(dev_dir).resolve()
    if not dev_dir.is_dir():
        raise FileNotFoundError(f"Dev assets directory {dev_dir} does not exist.")

    if not keep_hidden or dry_run:
        removed = clean_hidden(dev_dir, dry_run=dry_run)
        verb = "Would remove" if dry_run else "Removed"
        print(f"{verb} {len(removed)} hidden file(s)/director(ies) from {dev_dir}.")
        for path in removed:
            print(f"  {verb.split()[0].lower()}: {path}")
        if dry_run:
            return True

    output = Path(output)
    if not output.parent.exists():
        raise FileNotFoundError(f"Registry output directory {output.parent} does not exist.")

    print(f"Generating registry for files in {dev_dir} ...")
    pooch.make_registry(str(dev_dir), str(output))
    print(f"Wrote registry to {output}")

    if not verify:
        return True

    reference = Path(reference)
    if not reference.is_file():
        raise FileNotFoundError(f"Reference registry {reference} does not exist.")

    print(f"Verifying {output.name} against {reference.name} ...")
    return verify_against(parse_registry(output), parse_registry(reference))


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
        help="Directory of pulled asset files. Defaults to the $PSI_DATA_DEV_DIR environment variable.",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=DEV_REGISTRY,
        help="Path to write the generated development registry.",
    )
    parser.add_argument(
        "-r", "--reference",
        type=Path,
        default=PROD_REGISTRY,
        help="Shipped registry to verify the generated one against.",
    )
    parser.add_argument(
        "--keep-hidden",
        action="store_true",
        help="Do not remove hidden files/directories before generating.",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip verifying the generated registry against the reference.",
    )
    parser.add_argument(
        "-n", "--dry-run",
        action="store_true",
        help="Only report which hidden files would be removed, then stop.",
    )
    args = parser.parse_args(argv)
    if args.dev_dir is None:
        parser.error("no dev assets directory given and $PSI_DATA_DEV_DIR is not set")
    return args


def main(argv: Optional[list[str]] = None) -> None:
    args = parse_args(argv)
    ok = build_dev_registry(
        dev_dir=args.dev_dir,
        output=args.output,
        reference=args.reference,
        keep_hidden=args.keep_hidden,
        verify=not args.no_verify,
        dry_run=args.dry_run,
    )
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()