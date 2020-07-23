# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ..console import CONTEXT_SETTINGS
from .catalog import catalog
from .changes import changes
from .dashboard import dash
from .jmx import jmx
from .prometheus import prom
from .scripts import scripts
from .snmp import snmp

ALL_COMMANDS = (catalog, changes, dash, jmx, prom, scripts, snmp)


@click.group(context_settings=CONTEXT_SETTINGS, short_help='Collection of useful utilities')
def meta():
    """Anything here should be considered experimental.

    This `meta` namespace can be used for an arbitrary number of
    niche or beta features without bloating the root namespace.
    """
    pass


for command in ALL_COMMANDS:
    meta.add_command(command)
