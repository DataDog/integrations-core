.. Integrations Core documentation master file, created by
   sphinx-quickstart on Wed Sep 19 10:38:55 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Integrations Core API docs
==========================

.. warning:: For more general developer docs, how-to guides, and examples, please see the
             `official Datadog documentation website <https://docs.datadoghq.com/developers/>`_.


The Datadog Check Toolkit
-------------------------

The :ref:`datadog_checks_base` package provides a set of functionalities used by any Agent based Integration:

* :class:`~datadog_checks.base.checks.base.AgentCheck`, the base class that every Agent-based Integration is derived from.
* :ref:`Prometheus <prometheus>` and :ref:`OpenMetrics <openmetrics>` facilities.
* Boilerplate code implementing common operations.
* A testing framework that can be used independently of the Agent.

The :ref:`datadog_checks_dev` package provides tools to ease development and testing:

* A global ``pytest`` fixture exposing the test framework.
* Many utilities to assist with common tasks such as IO and environment setup/tear down.
* A rich CLI, :ref:`ddev`, to run tests & E2E environments, manage dependencies, create new integrations, etc.


Table of Contents
^^^^^^^^^^^^^^^^^

.. toctree::
    :maxdepth: 3

    datadog_checks_base
    datadog_checks_dev


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
