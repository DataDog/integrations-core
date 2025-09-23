# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command(short_help='Build documentation')
@click.option('--check', is_flag=True, help='Ensure links are valid')
@click.option('--pdf', is_flag=True, help='Also export the site as PDF')
@click.pass_obj
def build(app: Application, check, pdf):
    """
    Build documentation.
    """
    script = 'build-check' if check else 'build'
    with app.repo.path.as_cwd(
        env_vars={'HATCH_VERBOSITY': str(app.verbosity), 'ENABLE_PDF_SITE_EXPORT': '1' if pdf else '0'}
    ):
        app.platform.exit_with_command([sys.executable, '-m', 'hatch', 'run', f'docs:{script}'])
