# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ..console import CONTEXT_SETTINGS
from .changelog import changelog
from .integrations import integrations
from .integrations_changelog import integrations_changelog
from .requirements import requirements

ALL_COMMANDS = (changelog, requirements, integrations, integrations_changelog)


@click.group(context_settings=CONTEXT_SETTINGS, short_help='A collection of tasks related to the Datadog Agent')
def agent():
    pass


for command in ALL_COMMANDS:
    agent.add_command(command)
