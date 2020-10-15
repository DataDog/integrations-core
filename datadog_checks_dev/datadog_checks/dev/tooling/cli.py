# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from .commands import ALL_COMMANDS
from .commands.console import (
    CONTEXT_SETTINGS,
    echo_debug,
    echo_success,
    echo_waiting,
    echo_warning,
    set_color,
    set_debug,
)
from .config import CONFIG_FILE, config_file_exists, load_config, restore_config
from .constants import get_root
from .utils import initialize_root


@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.option('--core', '-c', is_flag=True, help='Work on `integrations-core`.')
@click.option('--extras', '-e', is_flag=True, help='Work on `integrations-extras`.')
@click.option('--agent', '-a', is_flag=True, help='Work on `datadog-agent`.')
@click.option('--marketplace', '-m', is_flag=True, help='Work on `marketplace`.')
@click.option('--here', '-x', is_flag=True, help='Work on the current location.')
@click.option('--color/--no-color', default=None, help='Whether or not to display colored output (default true).')
@click.option('--quiet', '-q', help='Silence output', is_flag=True)
@click.option('--debug', '-d', help='Include debug output', is_flag=True)
@click.version_option()
@click.pass_context
def ddev(ctx, core, extras, agent, marketplace, here, color, quiet, debug):
    if not quiet and not config_file_exists():
        echo_waiting('No config file found, creating one with default settings now...')

        try:
            restore_config()
            echo_success('Success! Please see `ddev config`.')
        except OSError:
            echo_warning(f'Unable to create config file located at `{CONFIG_FILE}`. Please check your permissions.')

    # Load and store configuration for sub-commands.
    config = load_config()

    msg = initialize_root(config, agent, core, extras, marketplace, here)
    if not quiet:
        if msg:
            echo_warning(msg)

        if debug:
            set_debug()
            echo_debug(f'Root directory set to: {get_root()}')

    if color is not None:
        config['color'] = color
    set_color(config['color'])

    # https://click.palletsprojects.com/en/7.x/api/#click.Context.obj
    ctx.obj = config

    if not ctx.invoked_subcommand:
        click.echo(ctx.get_help())


for command in ALL_COMMANDS:
    ddev.add_command(command)
