# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click
import os
from operator import itemgetter

from a7 import validate_py3

from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success
from ...constants import get_root, NOT_CHECKS
from ...utils import get_valid_checks


@click.command(
    context_settings=CONTEXT_SETTINGS,
    short_help="Verify if a custom check or integration can run on python 3"
)
@click.argument('check')
def py3(check):
    """Verify if a custom check or integration can run on python 3. CHECK
    can be an integration name or a valid path to a Python module or package folder.
    """

    root = get_root()
    if check == 'datadog_checks_base':
        path_to_module = os.path.join(root, check, 'datadog_checks', 'base')
    elif check in get_valid_checks() and check not in NOT_CHECKS:
        path_to_module = os.path.join(root, check, 'datadog_checks', check)
    else:
        path_to_module = check

    if not os.path.exists(path_to_module):
        abort(u"{} does not exist.".format(path_to_module))

    echo_info(u"Validating python3 compatibility of {}...".format(check))
    results = validate_py3(path_to_module)

    if results:
        echo_failure(u"Incompatibilities were found for {}:".format(check))
        current_path = None
        for problem in sorted(results, key=itemgetter("path")):
            # validate_py3 returns an array a dicts like
            # {
            #     "message": "Line 23, Column 8: Calling a dict.iter*() method",
            #     "file": "/path/to/file.py",
            # }
            path = problem["path"]
            if current_path is None or path != current_path:
                echo_info(u"File {}:".format(path))
            echo_failure("  {}".format(problem["message"]))
            current_path = path
        abort()
    else:
        echo_success(u"{} is compatible with python3".format(check))
