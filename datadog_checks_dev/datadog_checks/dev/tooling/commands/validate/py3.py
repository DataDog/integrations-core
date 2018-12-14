# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click
import os
import subprocess

from ..utils import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_warning
from ...constants import get_root, NOT_CHECKS
from ...utils import get_valid_checks


@click.command(
    context_settings=CONTEXT_SETTINGS,
    short_help="Verify if a custom check or integration will run on python 3"
)
@click.argument('check')
def py3(check):
    """Verify if a custom check or integration will run on python 3"""

    root = get_root()
    if check == 'datadog_checks_base':
        path_to_module = os.path.join(root, check, 'datadog_checks', 'base')
    elif check in get_valid_checks() and check not in NOT_CHECKS:
        path_to_module = os.path.join(root, check, 'datadog_checks', check)
    else:
        path_to_module = check

    if not os.path.exists(path_to_module):
        abort("{} does not exist.".format(path_to_module))

    echo_info("Validating python3 compatibility of {}".format(check))
    try:
        # Disable `no-absolute-import`, which checks for a behaviour that's already part of python 2.7
        # cf https://www.python.org/dev/peps/pep-0328/
        out = subprocess.check_output(["pylint", path_to_module, "--py3k", "--disable=no-absolute-import"])
    except subprocess.CalledProcessError as e:
        echo_failure("Incompatibilities were found for {}:".format(check))
        # The last 3 lines are for the pylint score
        for line in e.output.splitlines():
            line = line.strip()
            if line.startswith("----"):
                # No more errors
                break
            if line.startswith("*************"):
                # Line for the module where the issue is found
                echo_info("  {}".format(line))
            else:
                # Line describing the issue
                echo_failure("  {}".format(line))
        abort()

    if len(out.strip()) == 0:
        # No python files found by pylint
        echo_warning("Pylint found no python files to check for {}.".format(check))
        echo_warning("Be sure to specify the name of an integration, or a path to a python module")
    else:
        echo_success("{} is compatible with python3".format(check))
