# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import click

from .utils import CONTEXT_SETTINGS, abort, echo_info, echo_success, echo_waiting
from ..constants import get_root
from ..test import get_tox_envs, pytest_coverage_sources
from ...subprocess import run_command
from ...utils import chdir, file_exists, remove_path, running_on_ci


def display_envs(check_envs):
    for check, envs in check_envs:
        echo_success('`{}`:'.format(check))
        for e in envs:
            echo_info('    {}'.format(e))


@click.command(
    context_settings=CONTEXT_SETTINGS,
    short_help='Run tests'
)
@click.argument('checks', nargs=-1)
@click.option('--style', '-s', is_flag=True, help='Run only style checks')
@click.option('--bench', '-b', is_flag=True, help='Run only benchmarks')
@click.option('--cov', '-c', 'coverage', is_flag=True, help='Measure code coverage')
@click.option('--cov-missing', '-m', is_flag=True, help='Show line numbers of statements that were not executed')
@click.option('--pdb', 'enter_pdb', is_flag=True, help='Drop to PDB on first failure, then end test session')
@click.option('--debug', '-d', is_flag=True, help='Set the log level to debug')
@click.option('--verbose', '-v', count=True, help='Increase verbosity (can be used additively)')
@click.option('--list', '-l', 'list_envs', is_flag=True, help='List available test environments')
@click.option('--changed', is_flag=True, help='Only test changed checks')
@click.option('--cov-keep', is_flag=True, help='Keep coverage reports')
def test(checks, style, bench, coverage, cov_missing, enter_pdb, debug, verbose, list_envs, changed, cov_keep):
    """Run tests for Agent-based checks.

    If no checks are specified, this will only test checks that
    were changed compared to the master branch.

    You can also select specific comma-separated environments to test like so:

    \b
    $ ddev test mysql:mysql57,maria10130
    """
    if list_envs:
        check_envs = get_tox_envs(checks, every=True, sort=True)
        display_envs(check_envs)
        return

    root = get_root()
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

    check_envs = get_tox_envs(checks, style=style, benchmark=bench, changed_only=changed)
    tests_ran = False

    for check, envs in check_envs:
        # Many check don't have benchmark envs, etc.
        if not envs:
            continue

        # This is for ensuring proper spacing between output of multiple checks' tests.
        # Basically this avoids printing a new line before the first check's tests.
        output_separator = '\n' if tests_ran else ''

        # For performance reasons we're generating what to test on the fly and therefore
        # need a way to tell if anything ran since we don't know anything upfront.
        tests_ran = True

        if coverage:
            test_env_vars['PYTEST_ADDOPTS'] = pytest_options.format(pytest_coverage_sources(check))

        if verbose:
            echo_info('pytest options: `{}`'.format(test_env_vars['PYTEST_ADDOPTS']))

        with chdir(os.path.join(root, check), env_vars=test_env_vars):
            if style:
                test_type_display = 'only style checks'
            elif bench:
                test_type_display = 'only benchmarks'
            else:
                test_type_display = 'tests'

            wait_text = '{}Running {} for `{}`'.format(output_separator, test_type_display, check)
            echo_waiting(wait_text)
            echo_waiting('-' * len(wait_text))

            result = run_command('tox --develop -e {}'.format(','.join(envs)))
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

        echo_success('\nPassed!')

    if not tests_ran:
        echo_info('Nothing to test!')
