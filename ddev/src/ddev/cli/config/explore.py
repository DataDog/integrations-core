# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click


@click.command(short_help='Open the config location in your file manager')
@click.pass_obj
def explore(app):
    """Open the config location in your file manager."""
    click.launch(str(app.config_file.path), locate=True)
