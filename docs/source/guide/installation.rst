.. _installation:

Installation
============

.. attention::

    We highly recommend using a virtual environment to manage your Python packages and avoid conflicts with other
    projects. For the best results, we recommend using ``conda`` – *via* Miniforge (preferred), Miniconda, or Anaconda
    – to create and manage your virtual environments.

To get started with **psi-data**, you can install it directly from PyPI:

.. code-block:: bash

    pip install psi-data

This installs the package along with its only hard runtime dependency,
`pooch <https://www.fatiando.org/pooch/>`_, which manages downloading and caching
the data files.

Required Dependencies
---------------------
- `Python >= 3.8 <https://www.python.org/>`_
- `pooch <https://www.fatiando.org/pooch/>`_ — installed with the ``[progress]``
  extra so that downloads display a progress bar.

Companion Packages
------------------
``psi-data`` only *retrieves* data files; reading, analyzing, and visualizing
them is handled by the rest of the PSI Python ecosystem. The following packages
are not required to install or use ``psi-data``, but are the natural next steps
once the data are on disk:

- `psi-io <https://predsci.com/doc/psi-io/>`_ — read and write PSI HDF4/HDF5
  files and load coordinate-aware MHD model output.
- `mapflpy <https://predsci.com/doc/mapflpy/>`_ — trace magnetic field lines
  through MAS and POT3D vector fields.
- `pyvisual <https://predsci.com/doc/pyvisual/>`_ (PyPI: ``psi-pyvisual``) —
  interactive 3-D visualization of spherical MHD model output.
