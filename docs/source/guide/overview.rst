.. _overview:

Overview
========

``psi-data`` centers on a single module-level `pooch <https://www.fatiando.org/pooch/>`_
fetcher (the module-level ``FETCHER``) and a family of ``fetch_*``
helper functions. Each helper resolves the registry keys for the requested data,
downloads any files that are not already cached, verifies them against the
checksums recorded in the packaged registry, and returns their on-disk paths.

Because every download is checksum-verified and cached, calling a ``fetch_*``
function a second time is effectively free: the cached file is reused without
re-downloading. This makes ``psi-data`` well suited to documentation examples,
tutorials, and test fixtures that need real PSI model output without bundling
large binary files.

All public objects are importable directly from the top-level package:

.. code-block:: python

   import psi_data

   psi_data.fetch_mas_data         # MAS coronal / heliospheric MHD fields
   psi_data.fetch_mas_quantities   # MAS quantities at the inner radial boundary
   psi_data.fetch_pot3d_data       # POT3D potential-field components
   psi_data.fetch_all              # every file in the registry
   psi_data.clear_psi_cache        # remove the local download cache

Available Data
--------------

The bundled data come from a thermodynamic `MAS <https://www.predsci.com/mas/>`_
standard run for Carrington rotation 2309, driven by an HMI photospheric
magnetogram, together with a `POT3D <https://github.com/predsci/POT3D>`_
potential-field source-surface (PFSS) solution. Fields are defined on a
structured spherical grid :math:`(r, \theta, \varphi)` and follow PSI's HDF
storage conventions.

The variable names accepted by each fetcher are summarized below. For the
*physical meaning*, units, coordinate conventions, and mesh staggering of each
quantity, refer to the `psi-io overview
<https://predsci.com/doc/psi-io/guide/overview.html>`_, which documents the PSI
model quantities in detail.

.. list-table::
   :header-rows: 1
   :widths: 22 18 60

   * - Fetcher
     - Domain key(s)
     - Available variables
   * - :func:`~psi_data.fetch_mas_data`
     - ``cor``, ``hel``
     - ``br``, ``bt``, ``bp`` (:math:`\mathbf{B}`); ``vr``, ``vt``, ``vp``
       (:math:`\mathbf{v}`); ``jr``, ``jt``, ``jp`` (:math:`\mathbf{J}`); ``t``,
       ``rho``, ``p``; and, for the coronal domain only, the wave/heating
       quantities ``ep``, ``em``, ``zp``, ``zm``, ``heat``
   * - :func:`~psi_data.fetch_pot3d_data`
     - ``pot3d``
     - ``br``, ``bt``, ``bp`` (:math:`\mathbf{B}`)
   * - :func:`~psi_data.fetch_mas_quantities`
     - ``quantities``
     - ``ch_pm``

The coronal (``cor``) domain spans the low corona out to the source surface,
while the heliospheric (``hel``) domain extends from the source surface into the
inner heliosphere. When ``variables`` is omitted for a multi-domain MAS request,
only the variables common to *all* requested domains are fetched.

In addition to the model fields, three standalone example files are provided for
use in tutorials and tests:

- :func:`~psi_data.fetch_example_fieldline` — an example magnetic
  field line trace.
- :func:`~psi_data.fetch_example_radial_scale` — an example
  radial scaling profile.
- :func:`~psi_data.fetch_example_chmapdb` — an example
  coronal-hole map database (HDF5 only).

Quick Start
===========

Every fetcher accepts its target variables as a comma-separated string, as any
iterable of names, or as ``None`` to select a sensible default set. The MAS and
POT3D helpers return a ``Filepaths`` named tuple whose fields identify each file
and whose values are the cached :class:`~pathlib.Path` objects:

.. code-block:: python
   :linenos:

   import psi_data

   # A single domain / variable pair
   paths = psi_data.fetch_mas_data(domains="cor", variables="br")
   paths.cor_br                      # -> PosixPath('.../cor/mhd/br002.h5')

   # Multiple domains and variables at once
   paths = psi_data.fetch_mas_data(domains="cor,hel", variables="br,vr")
   paths._fields                     # -> ('cor_br', 'cor_vr', 'hel_br', 'hel_vr')

   # POT3D potential-field components (all three when variables is None)
   pot3d = psi_data.fetch_pot3d_data(variables=None)
   pot3d.br, pot3d.bt, pot3d.bp

The single-file example helpers return a lone :class:`~pathlib.Path`:

.. code-block:: python

   import psi_data

   fieldline = psi_data.fetch_example_fieldline()
   rscale = psi_data.fetch_example_radial_scale()

.. note::

   :func:`~psi_data.fetch_example_chmapdb` is only available in
   HDF5. Requesting it with ``hdf=4`` emits a
   :class:`~psi_data.RegistryWarning` and returns ``None`` rather
   than raising.

Selecting the HDF format
------------------------

Every fetcher accepts an ``hdf`` keyword selecting the file format to download:
``5`` for HDF5 (``.h5``, the default) or ``4`` for HDF4 (``.hdf``). An
unsupported value raises :exc:`ValueError`.

.. code-block:: python

   import psi_data

   h5_paths = psi_data.fetch_mas_data(domains="cor", variables="br", hdf=5)
   h4_paths = psi_data.fetch_mas_data(domains="cor", variables="br", hdf=4)

.. note::

   The HDF format is also inferred from the file extension by downstream PSI
   tools such as ``psi-io`` (``.hdf`` for HDF4, ``.h5`` for HDF5), so the files
   returned by ``psi-data`` can be passed straight through without specifying
   the format again.

Caching and offline use
------------------------

Downloaded files are stored in the platform-specific :mod:`pooch` cache,
resolved by :func:`pooch.os_cache` under the ``psi`` project name (for example,
``~/Library/Caches/psi`` on macOS or ``~/.cache/psi`` on Linux). Set the
:envvar:`PSI_DATA_CACHE` environment variable to override this location:

.. code-block:: bash

   export PSI_DATA_CACHE=/path/to/my/cache

To populate the cache up front — for example, before working offline — fetch the
entire registry for a given format with
:func:`~psi_data.fetch_all`:

.. code-block:: python

   import psi_data

   all_h5 = psi_data.fetch_all(hdf=5)   # download every HDF5 file

.. warning::

   :func:`~psi_data.fetch_all` downloads the complete data
   collection for the chosen format and may transfer a large volume of data on
   its first invocation.

To reclaim disk space, clear the cache with
:func:`~psi_data.clear_psi_cache`. By default it performs a
*dry run* (reporting what would be removed) and prompts for confirmation before
deleting; both the default OS cache and the :envvar:`PSI_DATA_CACHE` override are
considered:

.. code-block:: python

   import psi_data

   psi_data.clear_psi_cache()                            # dry run — nothing deleted
   psi_data.clear_psi_cache(dry_run=False)               # delete, with confirmation
   psi_data.clear_psi_cache(dry_run=False, prompt=False) # delete without prompting

Development mode
----------------

Setting the :envvar:`DEVELOPMENT` environment variable before importing
``psi_data`` redirects the fetcher to a local development server
(``http://localhost:8000``) and selects the development registry
(``registry-dev.txt``) instead of the published PSI asset host. This is intended
for maintainers regenerating or testing the registry against a local mirror of
the asset tree, and is not required for normal use.

Related Packages
================

``psi-data`` is the entry point for obtaining sample data; the companion PSI
packages consume the paths it returns. A typical workflow downloads a field,
reads it with `psi-io <https://predsci.com/doc/psi-io/>`_, and proceeds to
tracing or visualization.

**Reading a fetched field with psi-io:**

.. code-block:: python
   :linenos:

   import psi_data
   from psi_io import PsiData

   paths = psi_data.fetch_mas_data(domains="cor", variables="br")

   with PsiData(paths.cor_br, model="mas") as reader:
       br, r_scale, t_scale, p_scale = reader.read(mesh="main", unit="cgs")

**Tracing field lines** with `mapflpy <https://predsci.com/doc/mapflpy/>`_
requires the three magnetic field components, which a single MAS request
provides:

.. code-block:: python
   :linenos:

   import psi_data

   b = psi_data.fetch_mas_data(domains="cor", variables="br,bt,bp")
   bfiles = {"br": b.cor_br, "bt": b.cor_bt, "bp": b.cor_bp}
   # pass bfiles to a mapflpy Tracer / TracerMP instance

**Visualizing** the same fields is handled by
`pyvisual <https://predsci.com/doc/pyvisual/>`_, which renders structured-grid
slices, isosurfaces, and traced field lines from spherical
:math:`(r, \theta, \varphi)` coordinate arrays.

.. seealso::

   - `psi-io documentation <https://predsci.com/doc/psi-io/>`_ — reading and
     writing PSI HDF files, and the PSI data conventions.
   - `mapflpy documentation <https://predsci.com/doc/mapflpy/>`_ — magnetic
     field line tracing.
   - `pyvisual documentation <https://predsci.com/doc/pyvisual/>`_ — 3-D
     visualization of MHD model output.