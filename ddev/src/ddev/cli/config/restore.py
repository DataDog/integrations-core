# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command(short_help='Restore the config file to default settings')
@click.pass_obj
def restore(app: Application):
    """Restore the config file to default settings."""
    app.config_file.restore()
    app.display_success('Settings were successfully restored.')
    if app.config_file.overrides_available():
        delete_overrides = click.confirm(
            f"Overrides file found in '{app.config_file.overrides_path}'. Do you want to delete it?"
        )
        if delete_overrides:
            app.config_file.overrides_path.unlink()
            app.display_success('Overrides deleted.')
