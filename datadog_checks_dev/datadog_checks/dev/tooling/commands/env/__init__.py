# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ..utils import CONTEXT_SETTINGS
from .check import check_run
from .ls import ls
from .prune import prune
from .start import start
from .stop import stop


ALL_COMMANDS = (
    check_run,
    ls,
    prune,
    start,
    stop,
)


@click.group(
    context_settings=CONTEXT_SETTINGS,
    short_help='Manage environments'
)
def env():
    pass


for command in ALL_COMMANDS:
    env.add_command(command)
