# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ..console import CONTEXT_SETTINGS
from .build import build
from .changelog import changelog
from .make import make
from .show import show
from .stats import stats
from .tag import tag
from .trello import trello
from .upload import upload

ALL_COMMANDS = [build, changelog, make, show, stats, tag, trello, upload]


@click.group(context_settings=CONTEXT_SETTINGS, short_help='Manage the release of checks')
def release():
    pass


for command in ALL_COMMANDS:
    release.add_command(command)
