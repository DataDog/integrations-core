.. _ddev:

The Developer Toolkit
---------------------

Prerequisites
^^^^^^^^^^^^^

* Python 3.8+ needs to be available on your system. Python 2.7 is optional.
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

Command Tab Completion
^^^^^^^^^^^^^^^^^^^^^^

Many of the `ddev` commands have tab-completion enabled.
There are a couple of ways to activate this for your system. The first is to
execute the following in your shell:

.. code-block:: bash

    $ eval "$(_DDEV_COMPLETE=source ddev)"

or for `zsh`:

.. code-block:: bash

    $ eval "$(_DDEV_COMPLETE=source_zsh ddev)"

Hitting `tab` at any point in your `ddev` command will autocomplete with available
options.  Note that this will only work for `integrations-core` repo, and
not any of the extended repos `ddev` can support.

For a more permenant solution, you can add the lines to either your `.bashrc` or `.zhsrc`
files respectively, but this may introduce a bit of a lag on startup.  As an alternative,
run the following command then load the resulting file into your startup script:

.. code-block:: bash

    $ _DDEV_COMPLETE=source_zsh ddev > ddev-zsh-completion.sh

