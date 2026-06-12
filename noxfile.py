# noxfile.py
from __future__ import annotations

import re
import shutil
from pathlib import Path

import nox

nox.options.reuse_existing_virtualenvs = False

pyproject = nox.project.load_toml()
PY_VERSIONS = nox.project.python_versions(pyproject)

# Preferred single interpreter for non-matrix sessions: the major.minor from
# .python-version if present, otherwise the newest supported version.
try:
    txt = Path(".python-version").read_text(encoding="utf-8").strip().splitlines()[0]
    m = re.search(r"(\d+)\.(\d+)", txt)  # grab major.minor; ignore patch/suffix
    SYS_PYTHON = f"{m.group(1)}.{m.group(2)}" if m else PY_VERSIONS[-1]
except FileNotFoundError:
    SYS_PYTHON = PY_VERSIONS[-1]

PROJECT_NAME = pyproject["project"]["name"]
MODULE_NAME = PROJECT_NAME.replace("-", "_")
PROJECT_ROOT = Path(__file__).parent.resolve()

_ARTIFACTS = PROJECT_ROOT / ".nox" / "_artifacts"
DIST_DIR = _ARTIFACTS / "dist"
DOCDIST_DIR = _ARTIFACTS / "docs"


def _optional(group: str) -> list[str]:
    """Return an optional-dependency group from pyproject, or [] if absent."""
    return pyproject["project"].get("optional-dependencies", {}).get(group, [])


@nox.session(python=PY_VERSIONS)
def tests(session: nox.Session) -> None:
    """Install the package and run the test suite from a temp directory."""
    session.install(".")
    if deps := _optional("test"):
        session.install(*deps)

    # Run from a temp dir so tests exercise the *installed* package, not the
    # source tree. pytest config (rootdir, addopts) is resolved from pyproject.
    session.chdir(session.create_tmp())
    session.run("pytest", PROJECT_ROOT.as_posix(), *session.posargs)


@nox.session(python=SYS_PYTHON)
def lint(session: nox.Session) -> None:
    """Ruff lint check.

    .. note::
       Extra args pass through, e.g. ``nox -s lint -- --fix`` or ``-- --select ALL``.
    """
    session.install(*_optional("lint"))
    session.run("ruff", "check", MODULE_NAME, *session.posargs)


@nox.session(python=SYS_PYTHON)
def types(session: nox.Session) -> None:
    """Mypy type checking against the source tree."""
    session.install(".")
    session.install(*_optional("types"))
    session.run("mypy", MODULE_NAME, *session.posargs)


@nox.session(python=SYS_PYTHON)
def docs(session: nox.Session) -> None:
    """Build the Sphinx documentation against the installed package."""
    session.install(".")
    if deps := _optional("docs"):
        session.install(*deps)

    args = pyproject["tool"].get("sphinx_build", {}).get("addopts", [])
    src_dir = PROJECT_ROOT / "docs" / "source"
    out_dir = DOCDIST_DIR / "html"
    session.run("sphinx-build", src_dir.as_posix(), out_dir.as_posix(), *args)


@nox.session(python=SYS_PYTHON)
def build(session: nox.Session) -> None:
    """Build the wheel and sdist into the artifacts directory."""
    # 'build' is the PyPI name of the build frontend (the 'build' optional
    # group uses the conda-forge name 'python-build', which is unrelated on PyPI).
    session.install("build")
    session.run(
        "python", "-m", "build",
        "--sdist", "--wheel",
        "--outdir", DIST_DIR.as_posix(),
    )
    shutil.rmtree(PROJECT_ROOT / "build", ignore_errors=True)


@nox.session(python=SYS_PYTHON)
def qa(session: nox.Session) -> None:
    """Run lint, type-checking, tests, and docs in one entrypoint."""
    session.notify("lint")
    session.notify("types")
    session.notify(f"tests-{session.python}")
    session.notify("docs")


if __name__ == "__main__":
    nox.main()