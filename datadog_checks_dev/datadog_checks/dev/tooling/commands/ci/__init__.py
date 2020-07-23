# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ..console import CONTEXT_SETTINGS
from .setup import setup

ALL_COMMANDS = (setup,)


@click.group(context_settings=CONTEXT_SETTINGS, short_help='Collection of CI utilities')
def ci():
    """
    CI related utils.
    Anything here should be considered experimental.
    """
    pass


for command in ALL_COMMANDS:
    ci.add_command(command)
