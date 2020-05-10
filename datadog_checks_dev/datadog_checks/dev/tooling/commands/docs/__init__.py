# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ..console import CONTEXT_SETTINGS
from .build import build
from .deploy import deploy
from .serve import serve

ALL_COMMANDS = (build, deploy, serve)


@click.group(context_settings=CONTEXT_SETTINGS, short_help='Manage documentation')
def docs():
    pass


for command in ALL_COMMANDS:
    docs.add_command(command)
