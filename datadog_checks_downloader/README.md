# Datadog Checks Downloader

## Overview

This package provides the secure downloader used by the [Datadog Agent][1] to
download Agent-based Integrations (also known as _Checks_). Internally, it uses
[The Update Framework (TUF)][2] and [in-toto][3] in order to provide
_end-to-end verification_ of integrations between our developers and end-users.
There is a blog post forthcoming shortly that will explain in more detail the
security guarantees. Interested readers may also wish to consult our KubeCon
2018 [talk][4] for more details.

Presently, the downloader is limited to downloading packages of
[integrations-core][5], but not [integrations-extras][6].

## Installation

This package is expected to be built and included with the DataDog Agent
beginning with version 6.10.0. There is a blog post forthcoming shortly that
will explain in more detail how to use the Datadog Agent to transparently
download and install new or updated integrations.

## Development

Create a dedicated virtualenv and follow the instructions in this paragraph
to work with the check.

To install the check in dev mode:

```shell
pip install -e '.[deps]'
```

To download a new or updated integration, you may specify a precise
[version][7]:

```shell
python -m datadog_checks.downloader -vvvv datadog-$INTEGRATION --version X.Y.Z
```

Or you may leave the version unspecified to download the latest version:

```shell
python -m datadog_checks.downloader -vvvv datadog-$INTEGRATION
```


### Testing

You can use `ddev` to run the tests.

About how to install `ddev`, see https://docs.datadoghq.com/developers/integrations/python/ and https://datadoghq.dev/integrations-core/.

For running tests locally, you need to download some test data first. You should only have to do it the first time, and later after some updates to the data:

```shell
hatch run test-data:create
```

This will run the script under `tests/scripts/download_test_data.py`, which will get a partial copy from
the actual repository.

Then to run the tests:

```shell
ddev test datadog_checks_downloader
```


### (Legacy) Testing by Invoking Pytest Directly

You can select between online and offline tests when running testsuite using
pytest:

```shell
pytest -vvvv -m online     # Run tests that use data from publicly a accessible repository.
pytest -vvvv -m offline    # Run tests that use data stored in the Git repository.
```

For online tests, you can specify explicitly distribution and its version to
run tests against:

```shell
pytest -vvvv -m online --distribution-name datadog-active-directory --distribution-version 1.10.0
```

To run checks against content served from own local directory where TUF, in-toto and wheel files are present:

```shell
pytest -vvvv --local-dir=/path/to/dir --distribution-name datadog-active-directory --distribution-version 1.10.0
```


## Troubleshooting

Need help? Contact [Datadog support][9].

[1]: https://github.com/DataDog/datadog-agent
[2]: https://theupdateframework.com
[3]: https://in-toto.io
[4]: https://youtu.be/XAlvd4QXngs
[5]: https://github.com/DataDog/integrations-core
[6]: https://github.com/DataDog/integrations-extras
[7]: https://www.python.org/dev/peps/pep-0440/#version-scheme
[8]: https://tox.readthedocs.io/en/latest/install.html
[9]: https://docs.datadoghq.com/help/
