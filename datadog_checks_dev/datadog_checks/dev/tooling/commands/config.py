# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from fnmatch import fnmatch

import click
import toml

from ..config import (
    CONFIG_FILE,
    SECRET_KEYS,
    config_file_exists,
    read_config_file,
    read_config_file_scrubbed,
    restore_config,
    save_config,
    scrub_secrets,
    update_config,
)
from ..utils import string_to_toml_type
from .console import CONTEXT_SETTINGS, echo_info, echo_success


@click.group(context_settings=CONTEXT_SETTINGS, short_help='Manage the config file')
def config():
    pass


@config.command(context_settings=CONTEXT_SETTINGS, short_help='Edit the config file with your default EDITOR')
def edit():
    """Edit the config file with your default EDITOR."""
    click.edit(filename=CONFIG_FILE)


@config.command(context_settings=CONTEXT_SETTINGS, short_help='Open the config location in your file manager')
def explore():
    """Open the config location in your file manager."""
    click.launch(CONFIG_FILE, locate=True)


@config.command(context_settings=CONTEXT_SETTINGS, short_help='Show the location of the config file')
def find():
    """Show the location of the config file."""
    if ' ' in CONFIG_FILE:
        echo_info(f'"{CONFIG_FILE}"')
    else:
        echo_info(CONFIG_FILE)


@config.command(context_settings=CONTEXT_SETTINGS, short_help='Show the contents of the config file')
@click.option('--all', '-a', 'all_keys', is_flag=True, help='No not scrub secret fields')
def show(all_keys):
    """Show the contents of the config file."""
    if not config_file_exists():
        echo_info('No config file found! Please try `ddev config restore`.')
    else:
        if all_keys:
            echo_info(read_config_file().rstrip())
        else:
            echo_info(read_config_file_scrubbed().rstrip())


@config.command(context_settings=CONTEXT_SETTINGS, short_help='Update the config file with any new fields')
def update():
    """Update the config file with any new fields."""
    update_config()
    echo_success('Settings were successfully updated.')


@config.command(context_settings=CONTEXT_SETTINGS, short_help='Restore the config file to default settings')
def restore():
    """Restore the config file to default settings."""
    restore_config()
    echo_success('Settings were successfully restored.')


@config.command('set', context_settings=CONTEXT_SETTINGS, short_help='Assign values to config file entries')
@click.argument('key')
@click.argument('value', required=False)
@click.pass_context
def set_value(ctx, key, value):
    """Assigns values to config file entries. If the value is omitted,
    you will be prompted, with the input hidden if it is sensitive.

    \b
    `$ ddev config set github.user foo`

        New setting:
        [github]
        user = "foo"

    You can also assign values on a per-org basis.

    \b
    `$ ddev config set orgs.<ORG_NAME>.api_key`

        New setting:
        [orgs.<ORG_NAME>]
        api_key = "***********"
    """
    scrubbing = False
    if value is None:
        scrubbing = any(fnmatch(key, pattern) for pattern in SECRET_KEYS)
        value = click.prompt(f'Value for `{key}`', hide_input=scrubbing)

    if key in ('repos.core', 'repos.extras', 'repos.agent', 'repos.marketplace') and not value.startswith('~'):
        value = os.path.abspath(value)

    user_config = new_config = ctx.obj
    user_config.pop('repo_choice', None)

    data = [value]
    data.extend(reversed(key.split('.')))
    key = data.pop()
    value = data.pop()

    # Use a separate mapping to show only what has changed in the end
    branch_config_root = branch_config = {}

    # Consider dots as keys
    while data:
        default_branch = {value: ''}
        branch_config[key] = default_branch
        branch_config = branch_config[key]

        new_value = new_config.get(key)
        if not hasattr(new_value, 'get'):
            new_value = default_branch

        new_config[key] = new_value
        new_config = new_config[key]

        key = value
        value = data.pop()

    value = string_to_toml_type(value)
    branch_config[key] = new_config[key] = value

    save_config(user_config)

    output_config = scrub_secrets(branch_config_root) if scrubbing else branch_config_root
    echo_success('New setting:')
    echo_info(toml.dumps(output_config).rstrip())
