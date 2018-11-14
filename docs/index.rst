.. Integrations Core documentation master file, created by
   sphinx-quickstart on Wed Sep 19 10:38:55 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Integrations Core API docs
==========================

.. warning:: For more general developer docs, how-to guides, and examples, please see the
             `official Datadog documentation website <https://docs.datadoghq.com/developers/>`_.


The Base Check
--------------

The :ref:`datadog_checks_base` package provides a set of functionalities used by any Agent based Integration:

* :class:`~datadog_checks.base.checks.base.AgentCheck`, the base class that every Agent-based Integration is derived from.
* :ref:`Prometheus <prometheus>` and :ref:`OpenMetrics <openmetrics>` facilities.
* Boilerplate code implementing common operations.
* A testing framework that can be used independently of the Agent.

Table of Contents
^^^^^^^^^^^^^^^^^

.. toctree::
    :maxdepth: 3

    datadog_checks_base

The Developer Toolkit
---------------------

The Developer Toolkit is designed for use by any Agent-based integration and provides two layers of support:

* The :ref:`api` package, providing a Python API for use during development and testing.
* A rich CLI, :ref:`ddev`, to run tests & E2E environments, manage dependencies, create new integrations and much more.

`datadog-checks-dev` is distributed on PyPI as a universal wheel
and is available on Linux, macOS, and Windows, and supports Python 2.7/3.5+ and PyPy.

Table of Contents
^^^^^^^^^^^^^^^^^

.. toctree::
    :maxdepth: 2

    datadog_checks_dev


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
