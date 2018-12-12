# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ..utils import CONTEXT_SETTINGS
from .dep import dep
from .manifest import manifest
from .metadata import metadata
from .service_checks import service_checks
from .agent_reqs import agent_reqs
from .py3 import py3

ALL_COMMANDS = (
    dep,
    manifest,
    metadata,
    service_checks,
    agent_reqs,
    py3,
)

@click.group(
    context_settings=CONTEXT_SETTINGS,
    short_help='Verify certain aspects of the repo'
)
def validate():
    pass


for command in ALL_COMMANDS:
    validate.add_command(command)
