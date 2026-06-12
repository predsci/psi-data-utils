.. _development:

Contributing & Development
==========================

This page describes how to develop ``psi-data-utils`` and, in particular, how to
maintain the **data registry** — the manifest of downloadable files and their
checksums that drives every ``fetch_*`` helper. Because the package ships only
the registry (not the data), adding or updating a dataset is a coordinated,
two-sided operation: the files must be published to the PSI asset server *and*
the registry that points at them must be regenerated and committed.

.. important::

   The registry and the data are decoupled. A registry entry is useless unless
   the matching file is reachable at the production URL, and a file on the
   server is invisible to users unless it appears in the shipped registry. The
   workflow below keeps the two in lockstep.

Development install
-------------------

We recommend an isolated environment (``conda`` via Miniforge preferred):

.. code-block:: bash

   git clone https://github.com/predsci/psi-data-utils.git
   cd psi-data-utils
   pip install -e ".[all]"   # editable install + test/lint/docs/dev tooling

The editable install puts ``psi_data`` on the path so the scripts and tests work
from any directory. See :ref:`installation` for the runtime dependencies.

Environment variables
---------------------

The development scripts and the package itself are configured through a handful
of environment variables. During development these are conveniently kept in a
``.env`` file at the repository root.

.. envvar:: DEVELOPMENT

   When set to any non-empty value, :mod:`psi_data` fetches from the local
   development server (``http://localhost:8000``) and loads the development
   registry (``registry-dev.txt``) instead of the published host and shipped
   ``registry.txt``. Leave it **unset** for normal (production) use.

.. envvar:: PSI_DATA_DEV_DIR

   Local directory holding a mirror of the published asset tree. This is where
   :file:`pull_registry_data.py` writes, where new files are staged, and what
   the development server serves.

.. envvar:: PSI_DATA_CACHE

   Overrides the on-disk :mod:`pooch` download cache used by the ``fetch_*``
   helpers. Useful for steering cached downloads to a known location during
   testing.

A typical ``.env`` looks like:

.. code-block:: bash

   DEVELOPMENT=true
   PSI_DATA_DEV_DIR=/path/to/Data/assets/
   PSI_DATA_CACHE=/path/to/Data/cache/

.. note::

   A ``.env`` file is **not** loaded automatically by Python. Export the values
   into your shell (e.g. ``set -a; source .env; set +a``, ``direnv``, or your
   IDE's run configuration) before running the scripts.

The development scripts
-----------------------

All scripts live in ``scripts/`` and share a common ``argparse`` interface (run
any of them with ``--help``). The data-registry workflow uses four of them, in
order:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Script
     - Purpose
   * - :file:`pull_registry_data.py`
     - Mirror the published assets into :envvar:`PSI_DATA_DEV_DIR`, verifying
       each file's checksum on download.
   * - :file:`build_dev_registry.py`
     - Strip hidden files, regenerate ``registry-dev.txt`` from the mirror, and
       verify it against the shipped ``registry.txt``.
   * - :file:`run_development_server.py`
     - Serve :envvar:`PSI_DATA_DEV_DIR` over ``http://localhost:8000`` so the
       package can fetch from it under :envvar:`DEVELOPMENT`.
   * - :file:`generate_local_registry.py`
     - Lower-level registry generator (no cleaning or verification); used
       internally by the workflow and available for ad-hoc generation.

Two further utilities are independent of the registry workflow:

- :file:`clear_existing_cache.py` — remove the local :mod:`pooch` download
  cache (the default OS cache and the :envvar:`PSI_DATA_CACHE` override).
- :file:`convert_hdf4_to_hdf5.py` — convert a tree of HDF4 (``.hdf``) files to
  HDF5 (``.h5``).

Establishing a clean baseline
-----------------------------

Before changing anything, mirror the current production assets and confirm your
local copy matches the shipped registry exactly:

.. code-block:: bash

   # 1. Pull every file in the shipped registry into $PSI_DATA_DEV_DIR
   python scripts/pull_registry_data.py

   # 2. Clean, regenerate registry-dev.txt, and verify against registry.txt
   python scripts/build_dev_registry.py

At this point verification should **pass** — the mirror is a faithful copy of
production. This is your baseline.

Adding files to the registry
----------------------------

#. **Stage the new files** under :envvar:`PSI_DATA_DEV_DIR`, placing each file
   at the *exact* relative path it will have on the server. Registry keys are
   these relative paths, so the directory layout is the contract. For example, a
   new coronal density field would live at::

      $PSI_DATA_DEV_DIR/H5CR2309_hmi_mast_mas_std_0201/cor/mhd/rho002.h5

#. **Regenerate and inspect the diff.** Re-run the builder; the verification
   step now compares your updated mirror against the (still unchanged) shipped
   registry:

   .. code-block:: bash

      python scripts/build_dev_registry.py

   Your newly added files are reported as ``EXTRA`` (present locally, not yet in
   the shipped registry). **The ``EXTRA`` list is your changeset** — confirm it
   contains exactly the files you intended to add, with no ``MISSING`` entries
   (which would mean the mirror is incomplete) and no ``MISMATCH`` entries
   (which would mean an existing file was altered).

   Hidden files (``.DS_Store`` and the like) are deleted automatically before
   generation, so they never leak into the registry. Use ``--dry-run`` to
   preview what would be removed, or ``--keep-hidden`` to disable cleaning.

#. **Test locally.** Serve the mirror and exercise the fetchers against it with
   :envvar:`DEVELOPMENT` enabled:

   .. code-block:: bash

      # terminal 1 — serve the staged assets
      python scripts/run_development_server.py

      # terminal 2 — with DEVELOPMENT=true in the environment
      python -c "import psi_data; print(psi_data.fetch_mas_data(domains='cor', variables='rho'))"

   Because :envvar:`DEVELOPMENT` selects ``registry-dev.txt`` and the local
   server, this validates both the new registry entries and that the files are
   actually downloadable and pass their checksums. Run the test suite as well:

   .. code-block:: bash

      pytest

Publishing: server upload, then promote the registry
----------------------------------------------------

Once the development registry has been vetted and tested, publish in this order.

.. warning::

   **Upload the files to the production server first.** If you promote the
   registry before the data is reachable at the production URL, released users
   will get download failures for the new entries.

#. **Copy the new files to the PSI asset server**, where the production URL
   (``https://www.predsci.com/doc/assets/``) is served from. Use ``rsync`` with
   explicit permissions so the web server can read everything and so macOS cruft
   is excluded:

   .. code-block:: bash

      rsync -rlvz \
        --chmod=D755,F644 \
        --no-owner --no-group \
        --exclude='.DS_Store' --exclude='._*' \
        "$PSI_DATA_DEV_DIR"/   user@predsci-host:/path/to/doc/assets/

   ``--chmod=D755,F644`` forces world-readable files and traversable
   directories regardless of local permissions; ``--no-owner --no-group`` avoids
   carrying local ownership across. Add ``--dry-run`` first to preview, and only
   add ``--delete`` if you intend to mirror deletions as well.

#. **Promote the development registry to production.** Once the files are live
   on the server, overwrite the shipped registry with the vetted development
   version:

   .. code-block:: bash

      cp psi_data/registry/registry-dev.txt psi_data/registry/registry.txt

   ``registry.txt`` is the file shipped as package data and used in production
   (when :envvar:`DEVELOPMENT` is unset), so this is the step that exposes the
   new files to released users.

#. **Commit and push.**

   .. code-block:: bash

      git add psi_data/registry/registry.txt
      git commit -m "Add <description> to the asset registry"
      git push

.. note::

   ``registry-dev.txt`` is intentionally git-ignored (it is a regenerated build
   artifact); only ``registry.txt`` is tracked and shipped. Promotion is simply
   copying the vetted dev registry over the tracked one.

Running tests and building docs
-------------------------------

.. code-block:: bash

   pytest                              # test suite (see pyproject for config)
   python -m sphinx -b html docs/source docs/_build/html   # build the docs

When building the docs locally, leave :envvar:`DEVELOPMENT` unset unless a
``registry-dev.txt`` is present, since importing :mod:`psi_data` loads the
registry selected by that variable.