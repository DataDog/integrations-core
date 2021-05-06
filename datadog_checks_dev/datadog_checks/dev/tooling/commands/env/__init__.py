# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ..console import CONTEXT_SETTINGS
from .check import check_run
from .edit import edit
from .ls import ls
from .prune import prune
from .reload import reload_env
from .shell import shell
from .start import start
from .stop import stop
from .test import test

ALL_COMMANDS = (check_run, edit, ls, prune, reload_env, shell, start, stop, test)


@click.group(context_settings=CONTEXT_SETTINGS, short_help='Manage environments')
def env():
    pass


for command in ALL_COMMANDS:
    env.add_command(command)
