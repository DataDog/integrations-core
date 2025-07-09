# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from ddev.config.file import DDEV_TOML

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command(short_help='Edit the config file with your default editor')
@click.option('--overrides', is_flag=True, help=f'Edit the local config file ({DDEV_TOML})')
@click.pass_obj
def edit(app: Application, overrides: bool):
    """Edit the config file with your default editor."""
    if overrides and not app.config_file.overrides_available():
        app.abort('No local config file found.')

    file_to_edit = app.config_file.overrides_path if overrides else app.config_file.path
    click.edit(filename=str(file_to_edit))
