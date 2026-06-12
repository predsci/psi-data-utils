psi-data-utils Documentation
============================

**psi-data-utils** is developed and maintained by `Predictive Science Inc. (PSI)
<https://www.predsci.com/>`_ and provides lightweight, cached access to sample
solar and magnetohydrodynamic (MHD) datasets from the PSI data ecosystem. It
wraps `pooch <https://www.fatiando.org/pooch/>`_ to download model output and
example files on demand, verify them against packaged checksums, and cache them
locally so that repeated access is fast and offline-friendly.

The bundled data come from a thermodynamic `MAS <https://www.predsci.com/mas/>`_
standard run for Carrington rotation 2309 — spanning the coronal and
heliospheric domains — together with a `POT3D
<https://github.com/predsci/POT3D>`_ potential-field solution and a small
collection of standalone example files. All files follow PSI's HDF conventions
and are available in both HDF4 (``.hdf``) and HDF5 (``.h5``) formats.

``psi-data-utils`` is intended as a convenient data source for the wider PSI Python
ecosystem: download fields with a single ``fetch_*`` call, then read them with
`psi-io <https://predsci.com/doc/psi-io/>`_, trace field lines with
`mapflpy <https://predsci.com/doc/mapflpy/>`_, and visualize the results with
`pyvisual <https://predsci.com/doc/pyvisual/>`_.

.. code-block:: python

   import psi_data

   # Download (or load from cache) the coronal radial magnetic field
   paths = psi_data.fetch_mas_data(domains="cor", variables="br")
   print(paths.cor_br)   # -> cached path to br002.h5

To get started, visit the :ref:`installation` guide. For a tour of the available
datasets and the fetching/caching model that underpins the package, consult the
:ref:`overview` page.

.. toctree::
    :hidden:

    Guide <guide/index>
    API <api/index>