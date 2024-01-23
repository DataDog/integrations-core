# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ddev.cli.release.changelog.fix import fix
from ddev.cli.release.changelog.new import new


@click.group(short_help='Manage changelogs')
def changelog():
    """
    Manage changelogs.
    """


changelog.add_command(fix)
changelog.add_command(new)
