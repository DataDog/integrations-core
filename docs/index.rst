.. Integrations Core documentation master file, created by
   sphinx-quickstart on Wed Sep 19 10:38:55 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Integrations Core's API docs
============================

.. warning:: For more general developer docs, how-to guides and examples, please see the
             `Official Documentation website <https://docs.datadoghq.com/developers/>`_.


The Datadog Check Toolkit
-------------------------

The :ref:`datadog_checks` toolkit provides a set of functionalities used by any Agent based Integration.
In particular it provides:

* :meth:`datadog_checks.checks.base.AgentCheck`, the base class every Agent based Integration derives from.
* :ref:`Prometheus <prometheus>` and :ref:`OpenMetrics <openmetrics>` facilities.
* Boilerplate code implementing common operations.
* A testing framework used to run tests without the need of a running Agent.


Table of Contents
^^^^^^^^^^^^^^^^^

.. toctree::
    :maxdepth: 3

    datadog_checks


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
