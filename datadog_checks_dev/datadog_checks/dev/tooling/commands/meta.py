# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from .meta_commands import ALL_COMMANDS
from .utils import CONTEXT_SETTINGS


@click.group(
    context_settings=CONTEXT_SETTINGS,
    short_help='Collection of useful utilities'
)
def meta():
    pass


for command in ALL_COMMANDS:
    meta.add_command(command)
