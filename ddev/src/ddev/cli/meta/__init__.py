# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click
from ddev.tooling.commands.meta.catalog import catalog
from ddev.tooling.commands.meta.changes import changes
from ddev.tooling.commands.meta.create_commits import create_example_commits
from ddev.tooling.commands.meta.dashboard import dash
from ddev.tooling.commands.meta.jmx import jmx
from ddev.tooling.commands.meta.manifest import manifest
from ddev.tooling.commands.meta.prometheus import prom
from ddev.tooling.commands.meta.snmp import snmp
from ddev.tooling.commands.meta.windows import windows

from ddev.cli.meta.scripts import scripts


@click.group(short_help='Collection of useful utilities')
def meta():
    """Anything here should be considered experimental.

    This `meta` namespace can be used for an arbitrary number of
    niche or beta features without bloating the root namespace.
    """


meta.add_command(catalog)
meta.add_command(changes)
meta.add_command(create_example_commits)
meta.add_command(dash)
meta.add_command(jmx)
meta.add_command(manifest)
meta.add_command(prom)
meta.add_command(scripts)
meta.add_command(snmp)
meta.add_command(windows)
