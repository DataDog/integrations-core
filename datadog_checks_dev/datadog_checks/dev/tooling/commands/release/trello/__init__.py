# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import click

from ...console import CONTEXT_SETTINGS
from .status import status
from .testable import testable

ALL_COMMANDS = [status, testable]


@click.group(context_settings=CONTEXT_SETTINGS, short_help='Tools for interacting with Trello')
def trello():
    """
    Subcommands for interacting with Trello Release boards.

    \b
    To use Trello:
    1. Go to `https://trello.com/app-key` and copy your API key.
    2. Run `ddev config set trello.key` and paste your API key.
    3. Go to `https://trello.com/1/authorize?key=key&name=name&scope=read,write&expiration=never&response_type=token`,
       where `key` is your API key and `name` is the name to give your token, e.g. ReleaseTestingYourName.
       Authorize access and copy your token.
    4. Run `ddev config set trello.token` and paste your token.
    """
    pass


for command in ALL_COMMANDS:
    trello.add_command(command)
