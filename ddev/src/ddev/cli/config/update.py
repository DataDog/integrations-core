# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click


@click.command(short_help='Update the config file with any new fields')
@click.pass_obj
def update(app):  # no cov
    """Update the config file with any new fields."""
    app.config_file.update()
    app.display_success('Settings were successfully updated.')
