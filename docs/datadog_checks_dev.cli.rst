.. _ddev:

The Developer Toolkit
---------------------

Prerequisites
^^^^^^^^^^^^^

* Python 3.7+ needs to be available on your system. Python 2.7 is optional.
* Docker to run the full test suite.

Using a virtual environment is recommended.

Installation
^^^^^^^^^^^^
.. code-block:: bash

    $ pip install "datadog-checks-dev[cli]"

This results in a working executable, ``ddev``, in your PATH. The
help flag shortcut ``-h`` is available globally.

To always use the latest version, instead do:

.. code-block:: bash

    $ pip install -e "path/to/datadog_checks_dev[cli]"

Usage
^^^^^

Upon the first invocation, ``ddev`` will attempt to create the config file if it
does not yet exist. ``integrations-core`` will be the target if the path exists
unless otherwise specified, defaulting to the current location. This allows
for full functionality no matter where you are.

Commands
^^^^^^^^

.. click:: datadog_checks.dev.tooling.cli:ddev
   :prog: ddev
   :show-nested:
