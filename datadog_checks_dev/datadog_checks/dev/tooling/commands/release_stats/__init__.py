# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ..console import CONTEXT_SETTINGS
from .print_csv import print_csv

ALL_COMMANDS = (print_csv,)


@click.group(context_settings=CONTEXT_SETTINGS, short_help='A collection of tasks to generate reports about releases')
def release_stats():
    pass


for command in ALL_COMMANDS:
    release_stats.add_command(command)
