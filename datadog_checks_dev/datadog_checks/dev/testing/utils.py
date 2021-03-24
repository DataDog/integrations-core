# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from fnmatch import fnmatch

from datadog_checks.dev.tooling.git import files_changed

from .constants import NON_TESTABLE_FILES, TESTABLE_FILE_PATTERNS


PYTHON_MAJOR_PATTERN = r'py(\d)'


def construct_pytest_options(
    check,
    verbose=0,
    color=None,
    enter_pdb=False,
    debug=False,
    bench=False,
    latest_metrics=False,
    coverage=False,
    junit=False,
    marker='',
    test_filter='',
    pytest_args='',
    e2e=False,
):
    # Prevent no verbosity
    pytest_options = f'--verbosity={verbose or 1}'

    if not verbose:
        pytest_options += ' --tb=short'

    if color is not None:
        pytest_options += ' --color=yes' if color else ' --color=no'

    if enter_pdb:
        # Drop to PDB on first failure, then end test session
        pytest_options += ' --pdb -x'

    if debug:
        pytest_options += ' --log-level=debug -s'

    if bench:
        pytest_options += ' --benchmark-only --benchmark-cprofile=tottime'
    else:
        pytest_options += ' --benchmark-skip'

    if latest_metrics:
        pytest_options += ' --run-latest-metrics'
        marker = 'latest_metrics'

    if junit:
        test_group = 'e2e' if e2e else 'unit'
        pytest_options += (
            # junit report file must contain the env name to handle multiple envs
            # $TOX_ENV_NAME is a tox injected variable
            # See https://tox.readthedocs.io/en/latest/config.html#injected-environment-variables
            f' --junit-xml=.junit/test-{test_group}-$TOX_ENV_NAME.xml'
            # Junit test results class prefix
            f' --junit-prefix={check}'
        )

    if coverage:
        pytest_options += (
            # Located at the root of each repo
            ' --cov-config=../.coveragerc'
            # Use the same .coverage file to aggregate results
            ' --cov-append'
            # Show no coverage report until the end
            ' --cov-report='
            # This will be formatted to the appropriate coverage paths for each package
            ' {}'
        )

    if marker:
        pytest_options += f' -m "{marker}"'

    if test_filter:
        pytest_options += f' -k "{test_filter}"'

    if pytest_args:
        pytest_options += f' {pytest_args}'

    return pytest_options


def testable_files(files):
    """
    Given a list of files, return only those that match any of the TESTABLE_FILE_PATTERNS and are
    not blacklisted by NON_TESTABLE_FILES (metrics.yaml, auto_conf.yaml)
    """
    filtered = []

    for f in files:
        if f.endswith(NON_TESTABLE_FILES):
            continue

        match = any(fnmatch(f, pattern) for pattern in TESTABLE_FILE_PATTERNS)
        if match:
            filtered.append(f)

    return filtered


def get_changed_checks():
    # Get files that changed compared to `master`
    changed_files = files_changed()

    # Filter by files that can influence the testing of a check
    changed_files[:] = testable_files(changed_files)

    return {line.split('/')[0] for line in changed_files}


def get_tox_env_python_version(env):
    match = re.match(PYTHON_MAJOR_PATTERN, env)
    if match:
        return int(match.group(1))
