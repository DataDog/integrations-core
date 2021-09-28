# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re

import click

from datadog_checks.dev.tooling.annotations import annotate_warning
from datadog_checks.dev.tooling.constants import get_root

from ....subprocess import run_command
from ...utils import complete_valid_checks
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_warning

FILE_PATH_REGEX = r'(.+\/[^\/]+)\:(\d+)\:\s+(\w+\s+\=\=\>\s+\w+)'


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Validate spelling')
@click.argument('check', autocompletion=complete_valid_checks, required=False)
@click.option('--fix', is_flag=True, help='Apply suggested fix')
@click.pass_context
def typos(ctx, check, fix):
    """Validate spelling in the source code.

    If `check` is specified, only the directory is validated.
    Use codespell command line tool to detect spelling errors.
    """
    root = get_root()

    if check:
        path = os.path.join(root, check)
    else:
        path = root

    cmd = f"codespell {path} --config={root}/.codespell/setup.cfg"

    if fix:
        cmd += " -w"

    try:
        output, err, code = run_command(cmd, capture=True)
        if code == 0:
            echo_success("All files are valid!")
            abort()
        annotate_typos(output)
    except Exception as e:
        echo_info(f"Encountered error validating spell check: {e}")


def annotate_typos(output):
    echo_failure("Typo validation failed, please fix typos")
    parse_errors = output.split('\n')
    for line in parse_errors:
        m = re.match(FILE_PATH_REGEX, line)
        if m is None:
            continue

        file, num, suggestion = m.groups()
        annotate_warning(file, f"Detected typo: {suggestion}", line=num)
        echo_warning(line)
