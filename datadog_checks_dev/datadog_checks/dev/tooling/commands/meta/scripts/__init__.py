# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ...console import CONTEXT_SETTINGS
from .github_user import email2ghuser
from .metrics2md import metrics2md
from .remove_labels import remove_labels
from .upgrade_python import upgrade_python

ALL_COMMANDS = (email2ghuser, metrics2md, remove_labels, upgrade_python)


@click.group(context_settings=CONTEXT_SETTINGS, short_help='Miscellaneous scripts that may be useful')
def scripts():
    pass


for command in ALL_COMMANDS:
    scripts.add_command(command)
