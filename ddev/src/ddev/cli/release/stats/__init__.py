# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click
from datadog_checks.dev.tooling.commands.release.stats.stats import merged_prs, report


@click.group(short_help='A collection of tasks to generate reports about releases')
def stats():
    """
    A collection of tasks to generate reports about releases.
    """


stats.add_command(merged_prs)
stats.add_command(report)
