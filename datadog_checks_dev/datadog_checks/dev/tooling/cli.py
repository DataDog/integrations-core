# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import click

from ..utils import dir_exists
from .commands import ALL_COMMANDS
from .commands.console import CONTEXT_SETTINGS, echo_success, echo_waiting, echo_warning, set_color, set_debug
from .config import CONFIG_FILE, config_file_exists, load_config, restore_config
from .constants import REPO_CHOICES, set_root


@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.option('--core', '-c', is_flag=True, help='Work on `integrations-core`.')
@click.option('--extras', '-e', is_flag=True, help='Work on `integrations-extras`.')
@click.option('--agent', '-a', is_flag=True, help='Work on `datadog-agent`.')
@click.option('--here', '-x', is_flag=True, help='Work on the current location.')
@click.option('--color/--no-color', default=None, help='Whether or not to display colored output (default true).')
@click.option('--quiet', '-q', is_flag=True)
@click.option('--debug', '-d', is_flag=True)
@click.version_option()
@click.pass_context
def ddev(ctx, core, extras, agent, here, color, quiet, debug):
    if not quiet and not config_file_exists():
        echo_waiting('No config file found, creating one with default settings now...')

        try:
            restore_config()
            echo_success('Success! Please see `ddev config`.')
        # TODO: Remove IOError (and noqa: B014) when Python 2 is removed
        # In Python 3, IOError have been merged into OSError
        except (IOError, OSError, PermissionError):  # noqa: B014
            echo_warning(f'Unable to create config file located at `{CONFIG_FILE}`. Please check your permissions.')

    # Load and store configuration for sub-commands.
    config = load_config()

    repo_choice = 'core' if core else 'extras' if extras else 'agent' if agent else config.get('repo', 'core')
    config['repo_choice'] = repo_choice
    config['repo_name'] = REPO_CHOICES[repo_choice]

    if color is not None:
        config['color'] = color

    # https://click.palletsprojects.com/en/7.x/api/#click.Context.obj
    ctx.obj = config

    root = os.path.expanduser(config.get(repo_choice, ''))
    if here or not dir_exists(root):
        if not here and not quiet:
            repo = 'datadog-agent' if repo_choice == 'agent' else f'integrations-{repo_choice}'
            echo_warning(f'`{repo}` directory `{root}` does not exist, defaulting to the current location.')

        root = os.getcwd()

    set_root(root)
    set_color(config['color'])

    if debug and not quiet:
        set_debug()

    if not ctx.invoked_subcommand:
        click.echo(ctx.get_help())


for command in ALL_COMMANDS:
    ddev.add_command(command)
