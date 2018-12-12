# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click
import os
from pylint import epylint as lint

from ..utils import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_warning
from ...constants import get_root, NOT_CHECKS
from ...utils import get_valid_checks


@click.command(
    'py3',
    context_settings=CONTEXT_SETTINGS,
    short_help="Verify if a custom check or integration will run on python 3"
)
@click.argument('check', required=True)
def py3(check):
    """Verify if a custom check or integration will run on python 3"""

    root = get_root()
    if check == 'datadog_checks_base':
        path_to_module = os.path.join(root, check, 'datadog_checks', 'base')
    elif check in get_valid_checks() and check not in NOT_CHECKS:
        path_to_module = os.path.join(root, check, 'datadog_checks', check)
    else:
        if not os.path.exists(check):
            abort("{} does not exist.".format(check))
        path_to_module = check
    echo_info("Validating python3 compatibility of {}".format(check))
    out, _ = lint.py_run("{} --py3k --disable=no-absolute-import".format(path_to_module), return_std=True)
    lines = out.read().strip().splitlines()
    if len(lines) == 2:
        # No errors found by pylint
        echo_success("{} is compatible with python3".format(check))
    elif len(lines) == 0:
        # No python files found by pylint
        echo_warning("Pylint found no python files to check for {}.".format(check))
        echo_warning("Be sure to specify the name of an integration, or a path to a python module")
    else:
        echo_failure("Incompatibilities were found for {}:".format(check))
        # The last 3 lines are for the pylint score
        for line in lines[:-3]:
            line = line.strip()
            if line.startswith("*************"):
                # Line for the module where the issue is found
                echo_info("  {}".format(line))
            else:
                # Line describing the issue
                echo_failure("  {}".format(line))
        abort()
