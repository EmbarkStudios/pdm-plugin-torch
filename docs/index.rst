===================
🔦 pdm-plugin-torch
===================

A utility tool for selecting torch backend and version through PDM.

Development
============

Install `PDM <https://pdm.fming.dev/latest/#installation>`_ following the instructions on the
PDM site. Then install the package using ::

   pdm install -d


Motivation
====================


Pytorch supports multiple variants of hardware and compute
backends. Due to how Python versioning works and how Pytorch publishes
their packages; it is impossible to use all of these as dependencies,
optional or not. We still wanted to make it easy and quick to install
this package, and develop it.

This package plugins in to PDM to add support for managing multiple
torch versions as separate lockfiles. These are currently resolved
independently of your main dependencies, so we suggest keeping a torch
version in an optional dependency to ensure shared transitive
dependencies are locked.

Usage
=====

Currently PDM does not support specifying plugin-dependencies in your pyproject.toml. Thus, we suggest using a setup like the following:


.. code-block::

    [tool.pdm.scripts]
    post_install = "pdm plugin add pdm-plugin-torch==$VERSION"



Configuration
=============

These are the supported options:

.. code-block::

    [tool.pdm.plugins.torch]
    dependencies = [
       "torch==1.10.2"
    ]
    lockfile = "torch.lock"
    enable-cpu = true

    enable-rocm = true
    rocm-versions = ["4.2"]

    enable-cuda = true
    cuda-versions = ["cu111", "cu113"]



.. toctree::
   :maxdepth: 2
   :caption: Introduction
   :hidden:

   self
   coding-standard

.. toctree::
   :caption: Extras
   :hidden:
   :glob:

   Architecture Desicision Records <adr/README.md>

..
   .. include:: adr/README.md
	  :parser: myst_parser.sphinx_

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
