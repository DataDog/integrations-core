# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import click

from .utils import CONTEXT_SETTINGS, abort, echo_info, echo_success, echo_waiting
from ..constants import TESTABLE_FILE_EXTENSIONS, get_root
from ..utils import get_testable_checks
from ...subprocess import run_command
from ...utils import chdir, dir_exists, file_exists, read_file


def testable_files(files):
    """
    Given a list of files, return the files that have an extension listed in FILE_EXTENSIONS_TO_TEST
    """
    return [f for f in files if f.endswith(TESTABLE_FILE_EXTENSIONS)]


def files_changed():
    """
    Return the list of file changed in the current branch compared to `master`
    """
    with chdir(get_root()):
        result = run_command('git diff --name-only master...', capture='out')
    changed_files = result.stdout.splitlines()

    # Remove empty lines
    return [f for f in changed_files if f]


def check_requirements(check):
    """
    Assert the output of pip-compile is the same as the contents of
    `requirements.txt` for the given check
    """
    check_dir = os.path.join(get_root(), check)
    if not dir_exists(check_dir):
        abort('Unable to find folder `{}`'.format(check_dir))

    # Check the files are there
    req_in = os.path.join(check_dir, 'requirements.in')
    req_txt = os.path.join(check_dir, 'requirements.txt')
    if not (file_exists(req_in) and file_exists(req_txt)):
        abort('Target folder `{}` must contain `requirements.in` and `requirements.txt`.'.format(check_dir))

    # Get the output of pip-compile
    with chdir(check_dir):
        out_lines = run_command('pip-compile -n --generate-hashes', capture=True).stdout.splitlines()

    # Read the contents of `requirements.txt`
    if read_file(req_txt).splitlines() != out_lines:
        abort('`requirements.in` and `requirements.txt` are out of sync, please run pip-compile and try again.')

    echo_success('Requirements are in sync!')


@click.command(
    context_settings=CONTEXT_SETTINGS,
    short_help='Run tests'
)
@click.argument('checks', nargs=-1)
@click.option('--bench', '-b', is_flag=True, help='Run only benchmarks')
@click.option('--every', is_flag=True, help='Run every kind of test')
def test(checks, bench, every):
    """Run tests for Agent-based checks.

    If no checks are specified, this will only test checks that
    were changed compared to the master branch.
    """
    root = get_root()

    if not checks:
        # get the list of the files that changed compared to `master`
        changed_files = files_changed()

        # get the list of files that can change the implementation of a check
        files_requiring_tests = testable_files(changed_files)

        # get the integrations associated with changed files
        changed_checks = {line.split('/')[0] for line in files_requiring_tests}

        checks = sorted(changed_checks & get_testable_checks())
    else:
        checks = sorted(set(checks) & get_testable_checks())

    if not checks:
        echo_info('No checks to test!')
        return

    for check in checks:
        # check requirements.in and requirements.txt are in sync
        if not bench and check != 'datadog_checks_dev':
            echo_waiting('Verifying requirements are in sync for `{}`...'.format(check))
            check_requirements(check)
            click.echo()

        with chdir(os.path.join(root, check)):
            if every:
                wait_text = 'Running tests for `{}`'.format(check)
                echo_waiting(wait_text)
                echo_waiting('-' * len(wait_text))

                result = run_command('tox')
                if result.code:
                    abort('Failed!', code=result.code)
            else:
                env_list = run_command('tox --listenvs', capture='out').stdout
                env_list = [e.strip() for e in env_list.splitlines()]

                if bench:
                    benches = [e for e in env_list if e.startswith('bench')]
                    if benches:
                        wait_text = 'Running benchmarks for `{}`'.format(check)
                        echo_waiting(wait_text)
                        echo_waiting('-' * len(wait_text))

                        result = run_command('tox -e {}'.format(','.join(benches)))
                        if result.code:
                            abort('Failed!', code=result.code)
                else:
                    non_benches = [e for e in env_list if not e.startswith('bench')]
                    if non_benches:
                        wait_text = 'Running tests for `{}`'.format(check)
                        echo_waiting(wait_text)
                        echo_waiting('-' * len(wait_text))

                        result = run_command('tox -e {}'.format(','.join(non_benches)))
                        if result.code:
                            abort('Failed!', code=result.code)

        echo_success('Passed!')
