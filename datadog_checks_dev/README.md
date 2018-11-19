# Datadog Checks Dev

[![Latest PyPI version][1]][2]
[![Supported Python versions][3]][4]
[![License][5]][6]
[![Documentation Status][7]][8]

-----

This is the developer toolkit designed for use by any [Agent-based][9] check or
integration repository.

## Installation

`datadog-checks-dev` is distributed on [PyPI][10] as a universal wheel
and is available on Linux, macOS, and Windows, and supports Python 2.7/3.5+ and PyPy.

```console
$ pip install "datadog-checks-dev[cli]"
```

At this point there should be a working executable, ddev, in your PATH. The help flag shortcut -h is available globally.

## Documentation

Dev docs are hosted on [readthedocs][11]

[1]: https://img.shields.io/pypi/v/datadog-checks-dev.svg
[2]: https://pypi.org/project/datadog-checks-dev
[3]: https://img.shields.io/pypi/pyversions/datadog-checks-dev.svg
[4]: https://pypi.org/project/datadog-checks-dev
[5]: https://img.shields.io/pypi/l/datadog-checks-dev.svg
[6]: https://choosealicense.com/licenses
[7]: https://readthedocs.org/projects/datadog-checks-base/badge/?version=latest
[8]: https://datadog-checks-base.readthedocs.io/en/latest/?badge=latest
[9]: https://github.com/DataDog/datadog-agent
[10]: https://pypi.org
[11]: https://datadog-checks-base.readthedocs.io/en/latest/datadog_checks_dev.html