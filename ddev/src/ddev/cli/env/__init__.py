# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click
from datadog_checks.dev.tooling.commands.env.check import check_run
from datadog_checks.dev.tooling.commands.env.edit import edit
from datadog_checks.dev.tooling.commands.env.ls import ls
from datadog_checks.dev.tooling.commands.env.prune import prune
from datadog_checks.dev.tooling.commands.env.reload import reload_env
from datadog_checks.dev.tooling.commands.env.shell import shell
from datadog_checks.dev.tooling.commands.env.start import start
from datadog_checks.dev.tooling.commands.env.stop import stop
from datadog_checks.dev.tooling.commands.env.test import test


@click.group(short_help='Manage environments')
def env():
    """
    Manage environments.
    """


env.add_command(check_run)
env.add_command(edit)
env.add_command(ls)
env.add_command(prune)
env.add_command(reload_env)
env.add_command(shell)
env.add_command(start)
env.add_command(stop)
env.add_command(test)
