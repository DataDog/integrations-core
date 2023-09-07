# Testing

-----

The entrypoint for testing any integration is the command [`test`](ddev/cli.md#ddev-test).

Under the hood, we use [hatch][hatch] for environment management and [pytest][pytest-github] as our test framework.

## Discovery

Use the `--list`/`-l` flag to see what environments are available, for example:

```
$ ddev test postgres -l
                                      Standalone
┏━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Name   ┃ Type    ┃ Features ┃ Dependencies    ┃ Environment variables   ┃ Scripts   ┃
┡━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ lint   │ virtual │          │ black==22.12.0  │                         │ all       │
│        │         │          │ pydantic==2.0.2 │                         │ fmt       │
│        │         │          │ ruff==0.0.257   │                         │ style     │
├────────┼─────────┼──────────┼─────────────────┼─────────────────────────┼───────────┤
│ latest │ virtual │ deps     │                 │ POSTGRES_VERSION=latest │ benchmark │
│        │         │          │                 │                         │ test      │
│        │         │          │                 │                         │ test-cov  │
└────────┴─────────┴──────────┴─────────────────┴─────────────────────────┴───────────┘
                        Matrices
┏━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Name    ┃ Type    ┃ Envs       ┃ Features ┃ Scripts   ┃
┡━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━┩
│ default │ virtual │ py3.9-9.6  │ deps     │ benchmark │
│         │         │ py3.9-10.0 │          │ test      │
│         │         │ py3.9-11.0 │          │ test-cov  │
│         │         │ py3.9-12.1 │          │           │
│         │         │ py3.9-13.0 │          │           │
│         │         │ py3.9-14.0 │          │           │
└─────────┴─────────┴────────────┴──────────┴───────────┘
```

You'll notice that all environments for running tests are prefixed with `pyX.Y`, indicating the Python version to use.
If you don't have a particular version installed (for example Python 2.7), such environments will be skipped.

The second part of a test environment's name corresponds to the version of the product. For example, the `14.0` in `py3.9-14.0`
implies tests will run against version 14.x of PostgreSQL.

If there is no version suffix, it means that either:

1. the version is pinned, _usually_ set to pull the latest release, or
2. there is no concept of a product, such as the `disk` check

## Usage

### Explicit

Passing just the integration name will run every test environment. You may select a subset of environments
to run by appending a `:` followed by a comma-separated list of environments.

For example, executing:

```
ddev test postgres:py3.9-13.0,py3.9-11.0
```

will run tests for the environment `py3.9-13.0` followed by the environment `py3.9-11.0`.

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
─────────────────────────────── Coverage report ────────────────────────────────

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

## Linting

To run only the lint checks, use the `--lint`/`-s` shortcut flag.

You may also only run the formatter using the `--fmt`/`-fs` shortcut flag. The formatter will
automatically resolve the most common errors caught by the lint checks.

## Argument forwarding

You may pass arbitrary [arguments](https://docs.pytest.org/en/stable/reference/reference.html#command-line-flags)
directly to `pytest`, for example:

```
ddev test postgres -- -m unit --pdb -x
```
