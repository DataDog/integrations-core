# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ...console import CONTEXT_SETTINGS
from .changes import changes
from .ready import ready

ALL_COMMANDS = [changes, ready]


@click.group(context_settings=CONTEXT_SETTINGS, short_help='Show components of to be released checks')
def show():
    """To avoid GitHub's public API rate limits, you need to set
    `github.user`/`github.token` in your config file or use the
    `DD_GITHUB_USER`/`DD_GITHUB_TOKEN` environment variables.
    """
    pass


for command in ALL_COMMANDS:
    show.add_command(command)
