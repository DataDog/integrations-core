# Datadog Checks Dev

[![Latest PyPI version](https://img.shields.io/pypi/v/datadog-checks-dev.svg)](https://pypi.org/project/datadog-checks-dev)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/datadog-checks-dev.svg)](https://pypi.org/project/datadog-checks-dev)
[![License](https://img.shields.io/pypi/l/datadog-checks-dev.svg)](https://choosealicense.com/licenses)

-----

This is the developer toolkit designed for use by any [Agent-based][1] check or
integration repository. There are 2 layers: one purely for development/testing,
and the other for high level tasks such as releasing, dependency management, etc.

`datadog-checks-dev` is distributed on [PyPI](https://pypi.org) as a universal wheel
and is available on Linux, macOS, and Windows, and supports Python 2.7/3.5+ and PyPy.

**Table of Contents**

- [Management](#management)
  * [Installation](#installation-1)
  * [Usage](#usage-1)
    + [Clean](#clean)
    + [Config](#config)
      - [Find](#find)
      - [Restore](#restore)
      - [Set](#set)
      - [Show](#show)
      - [Update](#update)
    + [Dep](#dep)
      - [Freeze](#freeze)
      - [Pin](#pin)
      - [Resolve](#resolve)
      - [Verify](#verify)
    + [Manifest](#manifest)
      - [Set](#set-1)
      - [Verify](#verify-1)
    + [Release](#release)
      - [Changelog](#changelog)
      - [Freeze](#freeze-1)
      - [Make](#make)
      - [Show](#show-1)
        * [Changes](#changes)
        * [Ready](#ready)
      - [Tag](#tag)
      - [Upload](#upload)
    + [Test](#test)
- [Development](#development)
  * [Installation](#installation)
  * [Usage](#usage)

## Management

This is the layer that provides the developer CLI.

### Installation

```console
$ pip install datadog-checks-dev[cli]
```

At this point there should be a working executable, `ddev`, in your PATH. The
help flag shortcut `-h` is available globally.

### Usage

Upon the first invocation, `ddev` will attempt to create the config file if it
does not yet exist. `integrations-core` will be the target if the path exists
unless otherwise specified, defaulting to the current location. This allows
for full functionality no matter where you are.

```console
$ ddev
Usage: ddev [OPTIONS] COMMAND [ARGS]...

Options:
  -e, --extras  Work on `integrations-extras`.
  -x, --here    Work on the current location.
  -q, --quiet
  --version     Show the version and exit.
  -h, --help    Show this message and exit.

Commands:
  clean     Remove a project's build artifacts
  config    Manage the config file
  dep       Manage dependencies
  manifest  Manage manifest files
  release   Manage the release of checks
  test      Run tests
```

#### Clean

```console
$ ddev clean -h
Usage: ddev clean [OPTIONS] [CHECK]

  Removes a project's build artifacts.

  If `check` is not specified, the current working directory will be used.

  All `*.pyc`/`*.pyd`/`*.pyo`/`*.whl` files and `__pycache__` directories
  will be removed. Additionally, the following patterns will be removed from
  the root of the path: `.cache`, `.coverage`, `.eggs`, `.pytest_cache`,
  `.tox`, `build`, `dist`, and `*.egg-info`.

Options:
  -c, --compiled-only  Removes only .pyc files.
  -a, --all            Disable the detection of a project's dedicated virtual
                       env and/or editable installation. By default, these
                       will not be considered.
  -v, --verbose        Shows removed paths.
  -h, --help           Show this message and exit.
```

#### Config

```console
$ ddev config
Usage: ddev config [OPTIONS] COMMAND [ARGS]...

Options:
  -h, --help  Show this message and exit.

Commands:
  find     Show the location of the config file
  restore  Restore the config file to default settings
  set      Assign values to config file entries
  show     Show the contents of the config file
  update   Update the config file with any new fields
```

This config file looks like this:

```toml
core = "C:\\Users\\Ofek\\Desktop\\code\\integrations-core"
extras = "C:\\Users\\Ofek\\Desktop\\code\\integrations-extras"

[github]
user = "ofek"
token = "..."

[pypi]
user = "user"
pass = "..."
```

##### Find

```console
$ ddev config find -h
Usage: ddev config find [OPTIONS]

  Show the location of the config file.

Options:
  -h, --help  Show this message and exit.
```

##### Restore

```console
$ ddev config restore -h
Usage: ddev config restore [OPTIONS]

  Restore the config file to default settings.

Options:
  -h, --help  Show this message and exit.
```

##### Set

```console
$ ddev config set -h
Usage: ddev config set [OPTIONS] KEY [VALUE]

  Assigns values to config file entries. If the value is omitted, you will
  be prompted, with the input hidden if it is sensitive.

  $ ddev config set github.user ofek
  New setting:
  [github]
  user = "ofek"

Options:
  -h, --help  Show this message and exit.
```

##### Show

```console
$ ddev config show -h
Usage: ddev config show [OPTIONS]

  Show the contents of the config file.

Options:
  -a, --all   No not scrub secret fields
  -h, --help  Show this message and exit.
```

##### Update

```console
$ ddev config update -h
Usage: ddev config update [OPTIONS]

  Update the config file with any new fields.

Options:
  -h, --help  Show this message and exit.
```

#### Dep

```console
$ ddev dep
Usage: ddev dep [OPTIONS] COMMAND [ARGS]...

Options:
  -h, --help  Show this message and exit.

Commands:
  freeze   Combine all dependencies for the Agent's static environment
  pin      Pin a dependency for all checks that require it
  resolve  Resolve dependencies for any number of checks
  verify   Verify the uniqueness of dependency versions across all checks
```

##### Freeze

```console
$ ddev dep freeze -h
Usage: ddev dep freeze [OPTIONS]

  Combine all dependencies for the Agent's static environment.

Options:
  -l, --lazy  Do not attempt to upgrade transient dependencies
  -h, --help  Show this message and exit.
```

##### Pin

```console
$ ddev dep pin -h
Usage: ddev dep pin [OPTIONS] PACKAGE VERSION [CHECKS]...

  Pin a dependency for all checks that require it. This will also resolve
  transient dependencies.

  Setting the version to `none` will remove the package. You can specify an
  unlimited number of additional checks to apply the pin for via arguments.

Options:
  -l, --lazy   Do not attempt to upgrade transient dependencies
  -q, --quiet
  -h, --help   Show this message and exit.
```

##### Resolve

```console
$ ddev dep resolve -h
Usage: ddev dep resolve [OPTIONS] CHECKS...

  Resolve transient dependencies for any number of checks. If you want to do
  this en masse, put `all`.

Options:
  -l, --lazy   Do not attempt to upgrade transient dependencies
  -q, --quiet
  -h, --help   Show this message and exit.
```

##### Verify

```console
$ ddev dep verify -h
Usage: ddev dep verify [OPTIONS]

  Verify the uniqueness of dependency versions across all checks.

Options:
  -h, --help  Show this message and exit.
```

#### Manifest

```console
$ ddev manifest
Usage: ddev manifest [OPTIONS] COMMAND [ARGS]...

Options:
  -h, --help  Show this message and exit.

Commands:
  set     Assign values to manifest file entries for every check
  verify  Validate all `manifest.json` files
```

##### Set

```console
$ ddev manifest set -h
Usage: ddev manifest set [OPTIONS] KEY VALUE

  Assigns values to manifest file entries for every check.

Options:
  -h, --help  Show this message and exit.
```

##### Verify

```console
$ ddev manifest verify -h
Usage: ddev manifest verify [OPTIONS]

  Validate all `manifest.json` files.

Options:
  --fix                 Attempt to fix errors
  -i, --include-extras  Include optional fields
  -h, --help            Show this message and exit.
```

#### Release

```console
$ ddev release
Usage: ddev release [OPTIONS] COMMAND [ARGS]...

Options:
  -h, --help  Show this message and exit.

Commands:
  changelog  Update the changelog for a check
  freeze     Update the Agent's release and static dependency files
  make       Release a single check
  show       Show release information
  tag        Tag the git repo with the current release of a check
  upload     Build and upload a check to PyPI
```

##### Changelog

```console
$ ddev release changelog -h
Usage: ddev release changelog [OPTIONS] CHECK VERSION [OLD_VERSION]

  Perform the operations needed to update the changelog.

  This method is supposed to be used by other tasks and not directly.

Options:
  -n, --dry_run
  -h, --help     Show this message and exit.
```

##### Freeze

```console
$ ddev release freeze -h
Usage: ddev release freeze [OPTIONS]

  Write the `requirements-agent-release.txt` file at the root of the repo
  listing all the Agent-based integrations pinned at the version they
  currently have in HEAD. Also by default will create the Agent's static
  dependency file.

Options:
  --no-deps   Do not create the static dependency file
  -h, --help  Show this message and exit.
```

##### Make

```console
$ ddev release make -h
Usage: ddev release make [OPTIONS] CHECK VERSION

  Perform a set of operations needed to release a single check:

  * update the version in __about__.py
  * update the changelog
  * update the requirements-agent-release.txt file
  * commit the above changes

Options:
  -h, --help  Show this message and exit.
```

##### Show

> To avoid GitHub's public API rate limits, you need to set `github.user`/`github.token`
> in your config file or use the `DD_GITHUB_USER`/`DD_GITHUB_TOKEN` environment variables.

```console
$ ddev release show
Usage: ddev release show [OPTIONS] COMMAND [ARGS]...

  To avoid GitHub's public API rate limits, you need to set
  `github.user`/`github.token` in your config file or use the
  `DD_GITHUB_USER`/`DD_GITHUB_TOKEN` environment variables.

Options:
  -h, --help  Show this message and exit.

Commands:
  changes  Show all the pending PRs for a given check
  ready    Show all the checks that can be released
```

###### Changes

```console
$ ddev release show changes -h
Usage: ddev release show changes [OPTIONS] CHECK

  Show all the pending PRs for a given check.

Options:
  -h, --help  Show this message and exit.
```

###### Ready

```console
$ ddev release show ready -h
Usage: ddev release show ready [OPTIONS]

  Show all the checks that can be released.

Options:
  -q, --quiet
  -h, --help   Show this message and exit.
```

##### Tag

```console
$ ddev release tag -h
Usage: ddev release tag [OPTIONS] CHECK [VERSION]

  Tag the HEAD of the git repo with the current release number for a
  specific check. The tag is pushed to origin by default.

  Notice: specifying a different version than the one in __about__.py is a
  maintenance task that should be run under very specific circumstances
  (e.g. re-align an old release performed on the wrong commit).

Options:
  --push / --no-push
  -n, --dry_run
  -h, --help          Show this message and exit.
```

##### Upload

```console
$ ddev release upload -h
Usage: ddev release upload [OPTIONS] CHECK

  Release a specific check to PyPI as it is on the repo HEAD.

Options:
  -n, --dry_run
  -h, --help     Show this message and exit.
```

#### Test

```console
$ ddev test -h
Usage: ddev test [OPTIONS] [CHECKS]...

  Run tests for Agent-based checks.

  If no checks are specified, this will only test checks that were changed
  compared to the master branch.

Options:
  -b, --bench  Run only benchmarks
  --every      Run every kind of test
  -h, --help   Show this message and exit.
```

## Development

This is the layer intended to be used directly for testing.

### Installation

```console
$ pip install datadog-checks-dev
```

This comes with `pytest`, `mock`, and other core requirements for testing.
Most likely you will not install this manually, but rather list it as the
only dependency in a check's `requirements-dev.txt`.

### Usage

Aside from being a source for test dependencies, this also provides many useful
utilities and fixtures (soon!) to avoid re-inventing the wheel. They can all be
found [here][2].

Some examples:

```python
>>> import os
>>> from datadog_checks.dev import run_command, temp_chdir
>>>
>>> # Command can be a list or string
>>> result = run_command('python -c "import sys;print(sys.version)"', capture='out')
>>> result.stdout
'3.6.1 | packaged by conda-forge | (default, May 23 2017, 14:21:39) [MSC v.1900 64 bit (AMD64)]\r\n'
>>>
>>> os.getcwd()
'C:\\Users\\Ofek\\Desktop'
>>> with temp_chdir() as d:
...     d
...     os.getcwd()
...
'C:\\Users\\Ofek\\AppData\\Local\\Temp\\tmp5ef7c2ub'
'C:\\Users\\Ofek\\AppData\\Local\\Temp\\tmp5ef7c2ub'
>>> os.getcwd()
'C:\\Users\\Ofek\\Desktop'
```

In addition to being able to import `mock` itself, you also get a convenient `mocker`
fixture provided by [pytest-mock](https://github.com/pytest-dev/pytest-mock). It's a
thin-wrapper around `mock`'s patching API with the benefit of not having to worry
about undoing patches at the end of a test or nesting `with` statements.

Example from the docs:

```python
import os

class UnixFS:

    @staticmethod
    def rm(filename):
        os.remove(filename)

def test_unix_fs(mocker):
    mocker.patch('os.remove')
    UnixFS.rm('file')
    os.remove.assert_called_once_with('file')
```

[1]: https://github.com/DataDog/datadog-agent
[2]: https://github.com/DataDog/integrations-core/tree/master/datadog_checks_dev/datadog_checks/dev
