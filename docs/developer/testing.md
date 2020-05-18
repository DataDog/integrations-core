# Testing

-----

The entrypoint for testing any integration is the command `ddev test`, which accepts an arbitrary number of integrations as arguments.

Under the hood, we use [tox][tox-github] for environment management and [pytest][pytest-github] as our test framework.

## Discovery

Use the `--list`/`-l` flag to see what environments are available, for example:

```
$ ddev test postgres envoy -l
postgres:
    py27-10
    py27-11
    py27-93
    py27-94
    py27-95
    py27-96
    py38-10
    py38-11
    py38-93
    py38-94
    py38-95
    py38-96
    format_style
    style
envoy:
    py27
    py38
    bench
    format_style
    style
```

You'll notice that all environments for running tests are prefixed with `pyXY`, indicating the Python version to use.
If you don't have a particular version installed (for example Python 2.7), such environments will be skipped.

The second part of a test environment's name corresponds to the version of the product. For example, the `11` in `py38-11`
implies tests will run against version 11.x of PostgreSQL.

If there is no version suffix, it means that either:

1. the version is pinned, _usually_ set to pull the latest release, or
2. there is no concept of a product, such as the `disk` check

## Usage

### Explicit

Passing just the integration name will run every test environment e.g. executing `ddev test envoy`
will run the environments `py27`, `py38`, and `style`.

You may select a subset of environments to run by appending a `:` followed by a comma-separated list of environments.

For example, executing:

```
ddev test postgres:py38-11,style envoy:py38
```

will run, in order, the environments `py38-11` and `style` for the PostgreSQL check and the environment `py38` for the Envoy check.

### Detection

If no integrations are specified then only integrations that were changed will be tested, based on a diff between the latest commit to
the current and `master` branches.

The criteria for an integration to be considered changed is based on the file extension of paths in the diff. So for example if only
Markdown files were modified then nothing will be tested.

The integrations will be tested in lexicographical order.

## Coverage

To measure code coverage, use the `--cov`/`-c` flag. Doing so will display a summary of coverage statistics after successful execution
of integrations' tests.

```
$ ddev test tls -c
...
---------- Coverage report ----------

Name                              Stmts   Miss Branch BrPart  Cover
-------------------------------------------------------------------
datadog_checks\tls\__about__.py       1      0      0      0   100%
datadog_checks\tls\__init__.py        3      0      0      0   100%
datadog_checks\tls\tls.py           185      4     50      2    97%
datadog_checks\tls\utils.py          43      0     16      0   100%
tests\__init__.py                     0      0      0      0   100%
tests\conftest.py                   105      0      0      0   100%
tests\test_config.py                 47      0      0      0   100%
tests\test_local.py                 113      0      0      0   100%
tests\test_remote.py                189      0      2      0   100%
tests\test_utils.py                  15      0      0      0   100%
tests\utils.py                       36      0      2      0   100%
-------------------------------------------------------------------
TOTAL                               737      4     70      2    99%
```

To also show any line numbers that were not hit, use the `--cov-missing`/`-cm` flag instead.

```
$ ddev test tls -cm
...
---------- Coverage report ----------

Name                              Stmts   Miss Branch BrPart  Cover   Missing
-----------------------------------------------------------------------------
datadog_checks\tls\__about__.py       1      0      0      0   100%
datadog_checks\tls\__init__.py        3      0      0      0   100%
datadog_checks\tls\tls.py           185      4     50      2    97%   160-167, 288->275, 297->300, 300
datadog_checks\tls\utils.py          43      0     16      0   100%
tests\__init__.py                     0      0      0      0   100%
tests\conftest.py                   105      0      0      0   100%
tests\test_config.py                 47      0      0      0   100%
tests\test_local.py                 113      0      0      0   100%
tests\test_remote.py                189      0      2      0   100%
tests\test_utils.py                  15      0      0      0   100%
tests\utils.py                       36      0      2      0   100%
-----------------------------------------------------------------------------
TOTAL                               737      4     70      2    99%
```

## Style

To run only the style checking environments, use the `--style`/`-s` shortcut flag.

You may also only run the formatter environment using the `--format-style`/`-fs` shortcut flag. The formatter will
automatically resolve the most common errors caught by the style checker.

## Advanced

There are a number of shortcut options available that correspond to [pytest options][pytest-usage].

- `--marker`/`-m` (`pytest`: `-m`) - Only run tests matching a given marker expression e.g. `ddev test elastic:py38-7.2 -m unit`
- `--filter`/`-k` (`pytest`: `-k`) - Only run tests matching a given substring expression e.g.`ddev test redisdb -k replication`
- `--debug`/`-d` (`pytest`: `--log-level=debug -s`) - Set the log level to debug
- `--pdb` (`pytest`: `--pdb -x`) - Drop to PDB on first failure, then end test session
- `--verbose`/`-v` (`pytest`: `-v --tb=auto`) - Increase verbosity (can be used additively) and disables shortened tracebacks

You may also pass arguments directly to `pytest` using the `--pytest-args`/`-pa` option. For example, you could
re-write `-d` as `-pa "--log-level=debug -s"`.
