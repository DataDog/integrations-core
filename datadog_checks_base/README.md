# Datadog Checks Base

[![Latest PyPI version][1]][7]
[![Supported Python versions][2]][7]

## Overview

This package provides the Python bits needed by the [Datadog Agent][4]
to run Agent-based Integrations (also known as _Checks_).

This package is used in two scenarios:

1. When used from within the Python interpreter embedded in the Agent, it
provides all the base classes and utilities needed by any Check.

2. When installed in a local environment with a regular Python interpreter, it
mocks the presence of a running Agent so checks can work in standalone mode,
mostly useful for testing and development.

Please refer to the [docs][5] for details.

## Installation

Checks from [integrations-core][6] already
use the toolkit in a transparent way when you run the tests but you can
install the toolkit locally and play with it:

```shell
pip install datadog-checks-base
```

## Performance Optimizations

We strive to balance lean resource usage with a "batteries included" user experience.
This is why we import some of our dependencies inside functions that use them instead of the more conventional import section at the top of the file.

Below are some examples for how much we shave off the Python heap for a given dependency:

- `requests==2.32.3`: 3.6MB
- `RequestWrapper` class (`datadog_checks_base==37.7.0`): 2.9MB
- `prometheus-client==0.21.1`: around 1MB

This translates into even bigger savings when we run in the Agent, something close to 50MB.

## Troubleshooting

Need help? Contact [Datadog support][8].

[1]: https://img.shields.io/pypi/v/datadog-checks-base.svg
[2]: https://img.shields.io/pypi/pyversions/datadog-checks-base.svg
[4]: https://github.com/DataDog/datadog-agent
[5]: https://datadoghq.dev/integrations-core/base/about/
[6]: https://github.com/DataDog/integrations-core
[7]: https://pypi.org/project/datadog-checks-base/
[8]: https://docs.datadoghq.com/help/
[9]: https://github.com/scientific-python/lazy-loader
