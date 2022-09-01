# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click
from datadog_checks.dev.tooling.commands.docs.build import build
from datadog_checks.dev.tooling.commands.docs.deploy import deploy
from datadog_checks.dev.tooling.commands.docs.serve import serve


@click.group(short_help='Manage documentation')
def docs():
    """
    Manage documentation.
    """


docs.add_command(build)
docs.add_command(deploy)
docs.add_command(serve)
