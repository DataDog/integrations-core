# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ...console import CONTEXT_SETTINGS
from .stats import merged_prs, report

ALL_COMMANDS = (report, merged_prs)


@click.group(context_settings=CONTEXT_SETTINGS)
def stats():
    """Generate release statistics."""
    pass


for command in ALL_COMMANDS:
    stats.add_command(command)
