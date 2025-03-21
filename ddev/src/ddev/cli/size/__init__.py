# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import click

from ddev.cli.size.status import status


@click.group(short_help='Get the size of integrations and dependencies by platform and python version')
def size():
    """Package Size Analyzer"""
    pass


size.add_command(status)

if __name__ == "__main__":
    size()