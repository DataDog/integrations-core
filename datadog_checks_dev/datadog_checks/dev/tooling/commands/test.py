# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import click

from .utils import CONTEXT_SETTINGS, abort, echo_info, echo_success, echo_waiting
from ..constants import TESTABLE_FILE_EXTENSIONS, get_root
from ..git import files_changed
from ..utils import get_testable_checks
from ...subprocess import run_command
from ...utils import chdir


def testable_files(files):
    """
    Given a list of files, return the files that have an extension listed in FILE_EXTENSIONS_TO_TEST
    """
    return [f for f in files if f.endswith(TESTABLE_FILE_EXTENSIONS)]


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
                    benches = [e for e in env_list if 'bench' in e]
                    if benches:
                        wait_text = 'Running benchmarks for `{}`'.format(check)
                        echo_waiting(wait_text)
                        echo_waiting('-' * len(wait_text))

                        result = run_command('tox -e {}'.format(','.join(benches)))
                        if result.code:
                            abort('Failed!', code=result.code)
                else:
                    non_benches = [e for e in env_list if 'bench' not in e]
                    if non_benches:
                        wait_text = 'Running tests for `{}`'.format(check)
                        echo_waiting(wait_text)
                        echo_waiting('-' * len(wait_text))

                        result = run_command('tox -e {}'.format(','.join(non_benches)))
                        if result.code:
                            abort('Failed!', code=result.code)

        echo_success('Passed!')
