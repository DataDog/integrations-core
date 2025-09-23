# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ddev.cli.env.agent import agent
from ddev.cli.env.check import check
from ddev.cli.env.config import config
from ddev.cli.env.reload import reload_command
from ddev.cli.env.shell import shell
from ddev.cli.env.show import show
from ddev.cli.env.start import start
from ddev.cli.env.stop import stop
from ddev.cli.env.test import test_command


@click.group(short_help='Manage environments')
def env():
    """
    Manage environments.
    """


env.add_command(agent)
env.add_command(check)
env.add_command(config)
env.add_command(reload_command)
env.add_command(shell)
env.add_command(show)
env.add_command(start)
env.add_command(stop)
env.add_command(test_command)
