# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click
import json
import os
from contextlib import closing
from operator import itemgetter
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from pylint.lint import PyLinter, fix_import_path
from pylint.reporters.json import JSONReporter

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
        abort("{} does not exist.".format(path_to_module))

    echo_info("Validating python3 compatibility of {}...".format(check))
    with closing(StringIO()) as out:
        linter = PyLinter(reporter=JSONReporter(output=out))
        linter.load_default_plugins()
        linter.python3_porting_mode()
        # Disable `no-absolute-import`, which checks for a behaviour that's already part of python 2.7
        # cf https://www.python.org/dev/peps/pep-0328/
        linter.disable("no-absolute-import")
        with fix_import_path([path_to_module]):
            linter.check(path_to_module)
            linter.generate_reports()
        results = json.loads(out.getvalue() or "{}")

    if results:
        echo_failure("Incompatibilities were found for {}:".format(check))
        current_path = None
        for problem in sorted(results, key=itemgetter("path")):
            # An issue found by pylint is a dict like
            # {
            #     "message": "Calling a dict.iter*() method",
            #     "obj": "OpenFilesCheck.check",
            #     "column": 27,
            #     "path": "/path/to/file.py",
            #     "line": 235,
            #     "message-id": "W1620",
            #     "type": "warning",
            #     "symbol": "dict-iter-method",
            #     "module": "file"
            # }
            path = problem["path"]
            if current_path is None or path != current_path:
                echo_info("File {}:".format(path))
            echo_failure("  Line {}, column {}: {}".format(problem["line"], problem["column"], problem["message"]))
            current_path = path
        abort()
    else:
        echo_success("{} is compatible with python3".format(check))
