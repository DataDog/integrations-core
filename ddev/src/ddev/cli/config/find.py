# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click


@click.command(short_help='Show the location of the config file')
@click.pass_obj
def find(app):
    """Show the location of the config file."""
    app.display(str(app.config_file.path))
