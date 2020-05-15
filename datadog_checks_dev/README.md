# Datadog Checks Dev

[![Latest PyPI version][1]][2]
[![Supported Python versions][2]][2]
[![License][3]][5]
[![Documentation Status][4]][7]

-----

This is the developer toolkit designed for use by any [Agent-based][5] check or
integration repository.

## Prerequisites

* Python 3.8+ needs to be available on your system. Python 2.7 is optional.
* Docker to run the full test suite.

Using a virtual environment is recommended.

## Installation

`datadog-checks-dev` is distributed on [PyPI][6] as a universal wheel
and is available on Linux, macOS, and Windows, and supports Python 3.7+ and PyPy.

```console
$ pip install "datadog-checks-dev[cli]"
```

At this point there should be a working executable, ddev, in your PATH. The help flag shortcut -h is available globally.

## Documentation

Dev docs are hosted on [readthedocs][7]

[1]: https://img.shields.io/pypi/v/datadog-checks-dev.svg
[2]: https://img.shields.io/pypi/pyversions/datadog-checks-dev.svg
[3]: https://img.shields.io/pypi/l/datadog-checks-dev.svg
[4]: https://readthedocs.org/projects/datadog-checks-base/badge/?version=latest
[5]: https://github.com/DataDog/datadog-agent
[6]: https://pypi.org
[7]: https://datadog-checks-base.readthedocs.io/en/latest/datadog_checks_dev.html
