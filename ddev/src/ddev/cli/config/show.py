# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click


@click.command(short_help='Show the contents of the config file')
@click.option('--all', '-a', 'all_keys', is_flag=True, help='Do not scrub secret fields')
@click.pass_obj
def show(app, all_keys):
    """Show the contents of the config file."""
    if not app.config_file.path.is_file():  # no cov
        app.display_critical('No config file found! Please try `ddev config restore`.')
    else:
        from rich.syntax import Syntax

        text = app.config_file.read() if all_keys else app.config_file.read_scrubbed()
        app.output(Syntax(text.rstrip(), 'toml', background_color='default'))
