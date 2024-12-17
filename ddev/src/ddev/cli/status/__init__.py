# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command(short_help='Show information about the current environment')
@click.pass_obj
def status(app: Application):
    """Show information about the current environment."""
    app.display(f'Repo: {app.repo.name} @ {app.repo.path}')
    app.display(f'Branch: {app.repo.git.current_branch()}')
    app.display(f'Org: {app.config.org.name}')

    if changed_integrations := [i.name for i in app.repo.integrations.iter_changed()]:
        import shutil
        import textwrap

        app.display(
            textwrap.shorten(f'Changed: {", ".join(changed_integrations)}', width=shutil.get_terminal_size().columns)
        )
