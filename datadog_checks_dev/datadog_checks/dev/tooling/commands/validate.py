# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from .utils import CONTEXT_SETTINGS
from .validate_commands import ALL_COMMANDS


@click.group(
    context_settings=CONTEXT_SETTINGS,
    short_help='Verify certain aspects of the repo'
)
def validate():
    pass


for command in ALL_COMMANDS:
    validate.add_command(command)
