# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import click

from .utils import CONTEXT_SETTINGS, abort, echo_info, echo_success, echo_waiting
from ..constants import TESTABLE_FILE_EXTENSIONS, get_root
from ..git import files_changed
from ..utils import get_testable_checks
from ...structures import EnvVars
from ...subprocess import run_command
from ...utils import chdir, file_exists, remove_path, running_on_ci


def coverage_sources(check):
    # All paths are relative to each tox.ini
    if check == 'datadog_checks_base':
        package_path = 'datadog_checks'
    elif check == 'datadog_checks_dev':
        package_path = 'datadog_checks/dev'
    else:
        package_path = 'datadog_checks/{}'.format(check)

    return package_path, 'tests'


def pytest_coverage_sources(*checks):
    return ' '.join(
        ' '.join(
            '--cov={}'.format(source) for source in coverage_sources(check)
        )
        for check in checks
    )


def testable_files(files):
    """
    Given a list of files, return the files that have an extension listed in TESTABLE_FILE_EXTENSIONS
    """
    return [f for f in files if f.endswith(TESTABLE_FILE_EXTENSIONS)]


def get_changed_checks():
    # Get files that changed compared to `master`
    changed_files = files_changed()

    # Filter by files that can influence the testing of a check
    changed_files[:] = testable_files(changed_files)

    return {line.split('/')[0] for line in changed_files}


@click.command(
    context_settings=CONTEXT_SETTINGS,
    short_help='Run tests'
)
@click.argument('checks', nargs=-1)
@click.option('--bench', '-b', is_flag=True, help='Run only benchmarks')
@click.option('--cov', '-c', 'coverage', is_flag=True, help='Measure code coverage')
@click.option('--cov-missing', '-m', is_flag=True, help='Show line numbers of statements that were not executed')
@click.option('--pdb', 'enter_pdb', is_flag=True, help='Drop to PDB on first failure, then end test session')
@click.option('--debug', '-d', is_flag=True, help='Set the log level to debug')
@click.option('--verbose', '-v', count=True, help='Increase verbosity (can be used additively)')
@click.option('--changed', is_flag=True, help='Only test changed checks')
@click.option('--cov-keep', is_flag=True, help='Keep coverage reports')
def test(checks, bench, coverage, cov_missing, enter_pdb, debug, verbose, changed, cov_keep):
    """Run tests for Agent-based checks.

    If no checks are specified, this will only test checks that
    were changed compared to the master branch.
    """
    root = get_root()

    if checks:
        checks_to_test = get_testable_checks() & set(checks)
        if changed:
            checks_to_test = checks_to_test & get_changed_checks()
        # Retain order
        final_checks = []
        for check in checks:
            if check in checks_to_test:
                final_checks.append(check)
                checks_to_test.remove(check)
        checks = final_checks
    else:
        checks = sorted(get_testable_checks() & get_changed_checks())

    if not checks:
        echo_info('No checks to test!')
        return

    num_checks = len(checks)
    testing_on_ci = running_on_ci()

    # Start building pytest command line args
    pytest_options = '--verbosity={}'.format(verbose or 1)

    if enter_pdb:
        pytest_options = '--pdb -x {}'.format(pytest_options)

    if debug:
        pytest_options = '{} --log-level=debug'.format(pytest_options)

    if bench:
        pytest_options = '{} --benchmark-only --benchmark-cprofile=tottime'.format(pytest_options)
    else:
        pytest_options = '{} --benchmark-skip'.format(pytest_options)

    if coverage:
        pytest_options = '{} {}'.format(
            pytest_options,
            '--cov-config=../.coveragerc '
            '--cov-append '
            '--cov-report= {}'
        )

    test_env_vars = {
        'TOX_TESTENV_PASSENV': 'DDEV_COV_MISSING PYTEST_ADDOPTS',
        'DDEV_COV_MISSING': str(cov_missing or testing_on_ci),
        'PYTEST_ADDOPTS': pytest_options,
    }

    # Keep track of current check number so we avoid
    # printing a new line after the last test
    for i, check in enumerate(checks, 1):
        if coverage:
            test_env_vars['PYTEST_ADDOPTS'] = pytest_options.format(pytest_coverage_sources(check))

        if verbose:
            echo_info('pytest options: `{}`'.format(test_env_vars['PYTEST_ADDOPTS']))

        with chdir(os.path.join(root, check)):
            env_list = run_command('tox --listenvs', capture='out').stdout
            env_list = [e.strip() for e in env_list.splitlines()]

            with EnvVars(test_env_vars):
                if bench:
                    benches = [e for e in env_list if 'bench' in e]
                    if benches:
                        wait_text = 'Running benchmarks for `{}`'.format(check)
                        echo_waiting(wait_text)
                        echo_waiting('-' * len(wait_text))

                        result = run_command('tox --develop -e {}'.format(','.join(benches)))
                        if result.code:
                            abort('\nFailed!', code=result.code)
                else:
                    non_benches = [e for e in env_list if 'bench' not in e]
                    if non_benches:
                        wait_text = 'Running tests for `{}`'.format(check)
                        echo_waiting(wait_text)
                        echo_waiting('-' * len(wait_text))

                        result = run_command('tox --develop -e {}'.format(','.join(non_benches)))
                        if result.code:
                            abort('\nFailed!', code=result.code)

                if coverage and file_exists('.coverage'):
                    if not cov_keep:
                        echo_info('\n---------- Coverage report ----------\n')

                        result = run_command('coverage report --rcfile=../.coveragerc')
                        if result.code:
                            abort('\nFailed!', code=result.code)

                    if testing_on_ci:
                        result = run_command('coverage xml -i --rcfile=../.coveragerc')
                        if result.code:
                            abort('\nFailed!', code=result.code)

                        run_command('codecov -X gcov -F {} -f coverage.xml'.format(check))
                    else:
                        if not cov_keep:
                            remove_path('.coverage')
                            remove_path('coverage.xml')

        echo_success('\nPassed!{}'.format('' if i == num_checks else '\n'))
