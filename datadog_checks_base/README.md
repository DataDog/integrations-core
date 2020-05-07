# Datadog Checks Base

[![Latest PyPI version][1]][6]
[![Supported Python versions][2]][6]
[![Documentation Status][3]][8]

## Overview

This package provides the Python bits needed by the [Datadog Agent][4]
to run Agent-based Integrations (also known as _Checks_).

This package is used in two scenarios:

 1. When used from within the Python interpreter embedded in the Agent, it
 provides all the base classes and utilities needed by any Check.

 2. When installed in a local environment with a regular Python interpreter, it
 mocks the presence of a running Agent so checks can work in standalone mode,
 mostly useful for testing and development.

 Please refer to the [API docs][5] for details.

## Installation

Checks from [integrations-core][6] already
use the toolkit in a transparent way when you run the tests with Tox but you can
install the toolkit locally and play with it:

```shell
pip install datadog-checks-base
```

## Development

Create a dedicated virtualenv and follow the instructions in this paragraph
to work with the check.

To install the check in dev mode:

```shell
pip install -e .[dev]
```

To build the wheel package:

```shell
python setup.py bdist_wheel
```

To run the tests, [install tox][7] and just run:

```shell
tox
```

## Troubleshooting

Need help? Contact [Datadog support][8].

[1]: https://img.shields.io/pypi/v/datadog-checks-base.svg
[2]: https://img.shields.io/pypi/pyversions/datadog-checks-base.svg
[3]: https://readthedocs.org/projects/datadog-checks-base/badge/?version=latest
[4]: https://github.com/DataDog/datadog-agent
[5]: https://datadog-checks-base.readthedocs.io/en/latest/?badge=latest
[6]: https://github.com/DataDog/integrations-core
[7]: https://tox.readthedocs.io/en/latest/install.html
[8]: https://docs.datadoghq.com/help/
