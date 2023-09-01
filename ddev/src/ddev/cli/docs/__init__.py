# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ddev.cli.docs.build import build
from ddev.cli.docs.serve import serve


@click.group(short_help='Manage documentation')
def docs():
    """
    Manage documentation.
    """


docs.add_command(build)
docs.add_command(serve)
