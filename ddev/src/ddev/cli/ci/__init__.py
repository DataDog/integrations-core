# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click
from datadog_checks.dev.tooling.commands.ci.setup import setup


@click.group(short_help='Collection of CI utilities')
def ci():
    """
    CI related utils.
    Anything here should be considered experimental.
    """


ci.add_command(setup)
