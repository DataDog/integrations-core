# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import click

from .utils import CONTEXT_SETTINGS, echo_info
from ..git import files_changed
from ..constants import TESTABLE_FILE_EXTENSIONS
from ..utils import get_testable_checks


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
    short_help='Print out changed checks'
)
def changed():
    checks = sorted(get_testable_checks() & get_changed_checks())

    for check in checks:
        echo_info(check)
