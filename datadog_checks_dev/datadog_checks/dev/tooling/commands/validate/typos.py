# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click
import os
import subprocess

from ...utils import complete_valid_checks
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_warning

from datadog_checks.dev.tooling.constants import get_root


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Validate spelling')
@click.argument('check', autocompletion=complete_valid_checks, required=False)
@click.option('--fix', is_flag=True, help='Apply suggested fix')
@click.pass_context
def typos(ctx, check, fix):
    """Validate spelling in the source code

    If `check` is specified, only the directory is validated
    """
    cmd = "codespell {} --config={}/.codespell/setup.cfg"
    path = get_root()
    if check:
        path = os.path.join(path, check)
        path += '/'

    if fix:
        cmd += " -w"

    try:
        output = subprocess.run(cmd.format(path, path), shell=True)

        if output == 0:
            echo_success("All files are valid!")
        else:
            annotate_typos(output)
    except Exception as e:
        echo_info(f"Encountered error validating spell check: {e}")


def annotate_typos(output):
    pass