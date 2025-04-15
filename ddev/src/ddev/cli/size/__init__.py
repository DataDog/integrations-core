# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import click

from ddev.cli.size.diff import diff
from ddev.cli.size.status import status
from ddev.cli.size.timeline import timeline

@click.group(short_help='Get the size of integrations and dependencies by platform and python version')
def size():
    """Package Size Analyzer"""
    pass


size.add_command(status)
size.add_command(diff)
size.add_command(timeline)

if __name__ == "__main__":
    size()
