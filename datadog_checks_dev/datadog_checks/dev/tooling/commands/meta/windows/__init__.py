# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ...console import CONTEXT_SETTINGS
from .pdh import pdh

ALL_COMMANDS = [pdh]


@click.group(context_settings=CONTEXT_SETTINGS)
def windows():
    """Manage Windows-specific tools."""
    pass


for command in ALL_COMMANDS:
    windows.add_command(command)
