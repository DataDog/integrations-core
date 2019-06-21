# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ..console import CONTEXT_SETTINGS
from .agent_reqs import agent_reqs
from .config import config
from .dep import dep
from .logos import logos
from .manifest import manifest
from .metadata import metadata
from .py3 import py3
from .service_checks import service_checks

ALL_COMMANDS = (agent_reqs, config, dep, logos, manifest, metadata, py3, service_checks)


@click.group(context_settings=CONTEXT_SETTINGS, short_help='Verify certain aspects of the repo')
def validate():
    pass


for command in ALL_COMMANDS:
    validate.add_command(command)
