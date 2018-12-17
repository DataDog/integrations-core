# Datadog Checks Base

[![Latest PyPI version][5]][6]
[![Supported Python versions][9]][6]
[![Documentation Status][7]][8]

## Overview

This package provides the Python bits needed by the [Datadog Agent][1]
to run Agent-based Integrations (also known as _Checks_).

This package is used in two scenarios:

 1. When used from within the Python interpreter embedded in the Agent, it
 provides all the base classes and utilities needed by any Check.

 2. When installed in a local environment with a regular Python interpreter, it
 mocks the presence of a running Agent so checks can work in standalone mode,
 mostly useful for testing and development.

 Please refer to the [API docs][8] for details.

## Installation

Checks from [integrations-core][2] already
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

To run the tests, [install tox][3] and just run:

```shell
tox
```

## Troubleshooting

Need help? Contact [Datadog support][4].

[1]: https://github.com/DataDog/datadog-agent
[2]: https://github.com/DataDog/integrations-core
[3]: https://tox.readthedocs.io/en/latest/install.html
[4]: https://docs.datadoghq.com/help/
[5]: https://img.shields.io/pypi/v/datadog-checks-base.svg
[6]: https://pypi.org/project/datadog-checks-base
[7]: https://readthedocs.org/projects/datadog-checks-base/badge/?version=latest
[8]: https://datadog-checks-base.readthedocs.io/en/latest/?badge=latest
[9]: https://img.shields.io/pypi/pyversions/datadog-checks-base.svg
