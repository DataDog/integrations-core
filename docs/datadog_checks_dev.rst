.. _datadog_checks_dev:

datadog_checks_dev
==================

.. toctree::
    :maxdepth: 3

    datadog_checks_dev.api
    datadog_checks_dev.cli

Installation
------------

.. code-block:: bash

    $ pip install "datadog-checks-dev[cli]"

At this point there should be a working executable, :ref:`ddev`, in your PATH.
The help flag shortcut ``-h`` is available globally.

To always use the latest version, instead do:

.. code-block:: bash

    $ pip install -e "path/to/datadog_checks_dev[cli]"
