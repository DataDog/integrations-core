# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click


@click.command(short_help='Edit the config file with your default editor')
@click.pass_obj
def edit(app):
    """Edit the config file with your default editor."""
    click.edit(filename=str(app.config_file.path))
