# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command(short_help='Serve documentation')
@click.pass_obj
def serve(app: Application):
    """
    Serve documentation.
    """
    command = [sys.executable, '-m', 'hatch', 'run', 'docs:serve']
    with app.repo.path.as_cwd(env_vars={'HATCH_VERBOSITY': str(app.verbosity)}):
        app.platform.exit_with_command(command)
