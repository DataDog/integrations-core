# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import click

from ddev.cli.config.edit import edit
from ddev.cli.config.explore import explore
from ddev.cli.config.find import find
from ddev.cli.config.restore import restore
from ddev.cli.config.set import set_value
from ddev.cli.config.show import show


@click.group(short_help='Manage the config file')
def config():
    pass


config.add_command(edit)
config.add_command(explore)
config.add_command(find)
config.add_command(restore)
config.add_command(set_value)
config.add_command(show)
