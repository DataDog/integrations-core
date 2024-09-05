# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ddev.cli.release.branch.create import create
from ddev.cli.release.branch.tag import tag


@click.group(short_help='Manage release branches')
def branch():
    """
    Manage Agent release branches.
    """


branch.add_command(create)
branch.add_command(tag)
