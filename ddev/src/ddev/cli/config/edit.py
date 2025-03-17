# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command(short_help='Edit the config file with your default editor')
@click.option('--local', is_flag=True, help='Edit the local config file (.ddev.toml)')
@click.pass_obj
def edit(app: 'Application', local: bool):
    """Edit the config file with your default editor."""
    file_to_edit = app.config_file.local_path if local else app.config_file.path
    click.edit(filename=str(file_to_edit))
