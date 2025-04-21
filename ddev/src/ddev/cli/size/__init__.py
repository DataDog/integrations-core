# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import click

from ddev.cli.size.diff import diff
from ddev.cli.size.status import status
from ddev.cli.size.timeline import timeline


@click.group()
def size():
    """
    Analyze the download size of integrations and dependencies in various modes.

    This command provides tools to inspect, compare, and monitor size changes of modules
    across different commits, platforms, and Python versions.

    Available subcommands:
      • status   Show the current sizes of all modules
      • diff     Compare sizes between two commits
      • timeline Show the size evolution of a module over time

    Use `ddev size <subcommand> --help` for more details on each mode.
    """

    pass


size.add_command(status)
size.add_command(diff)
size.add_command(timeline)

if __name__ == "__main__":
    size()
