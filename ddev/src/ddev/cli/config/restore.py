# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click


@click.command(short_help='Restore the config file to default settings')
@click.pass_obj
def restore(app):
    """Restore the config file to default settings."""
    app.config_file.restore()
    app.display_success('Settings were successfully restored.')
