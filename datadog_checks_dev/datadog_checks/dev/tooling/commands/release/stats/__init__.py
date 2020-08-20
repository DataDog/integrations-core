# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ...console import CONTEXT_SETTINGS
from .csv_report import csv_report

ALL_COMMANDS = (csv_report,)


@click.group(context_settings=CONTEXT_SETTINGS, short_help='A collection of tasks to generate reports about releases')
def stats():
    pass


for command in ALL_COMMANDS:
    stats.add_command(command)
