# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from .env_commands import ALL_COMMANDS
from .utils import CONTEXT_SETTINGS


@click.group(
    context_settings=CONTEXT_SETTINGS,
    short_help='Manage environments'
)
def env():
    pass


for command in ALL_COMMANDS:
    env.add_command(command)
