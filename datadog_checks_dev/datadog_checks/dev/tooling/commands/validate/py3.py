# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from operator import itemgetter

import click

from ....subprocess import run_command
from ...utils import get_valid_checks, get_version_file
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success


@click.command(
    context_settings=CONTEXT_SETTINGS, short_help="Verify if a custom check or integration can run on python 3"
)
@click.argument('check')
def py3(check):
    """Verify if a custom check or integration can run on python 3. CHECK
    can be an integration name or a valid path to a Python module or package folder.
    """

    if check in get_valid_checks():
        path_to_module = os.path.dirname(get_version_file(check))
    else:
        path_to_module = check

    if not os.path.exists(path_to_module):
        abort(u"{} does not exist.".format(path_to_module))

    echo_info(u"Validating python3 compatibility of {}...".format(check))
    cmd = ["pylint", "-f", "json", "--py3k", "-d", "W1618", "--persistent", "no", "--exit-zero", path_to_module]
    echo_info(u"\tRunning: {}".format(' '.join(cmd)))

    output = run_command(cmd, capture='stdout', check=True).stdout
    results = json.loads(output) if output else None

    if results:
        echo_failure(u"Incompatibilities were found for {}:".format(check))
        current_path = None
        for problem in sorted(results, key=itemgetter("path")):
            # pylint returns an array a dicts like
            # {
            #     "line": 23,
            #     "column": 8,
            #     "message": "Calling a dict.iter*() method",
            #     "file": "/path/to/file.py",
            # }
            path = problem["path"]
            if current_path is None or path != current_path:
                echo_info(u"File {}:".format(path))
            echo_failure("  Line {}, column {}: {}".format(problem['line'], problem['column'], problem["message"]))
            current_path = path
        abort()
    else:
        echo_success(u"{} is compatible with python3".format(check))
