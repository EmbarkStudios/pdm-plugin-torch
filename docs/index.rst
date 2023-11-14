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

PDM supports specifying plugin-dependencies in your pyproject.toml, which is the suggested installation method. Note that in `pdm-plugin-torch` versions before 23.4.0, our configuration was in `tool.pdm.plugins.torch`. If upgrading, you'll need to also change that to `tool.pdm.plugin.torch`.


.. code-block::

    [tool.pdm]
	plugins = ["pdm-plugin-torch>=$VERSION"]

It is also suggested to use a `post_lock` hook to update the lockfile when a regular lock is made:

.. code-block::

    [tool.pdm.scripts]
    post_lock = "pdm torch lock"


Configuration
=============

These are the supported options:

.. code-block::

    [tool.pdm.plugin.torch]
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
