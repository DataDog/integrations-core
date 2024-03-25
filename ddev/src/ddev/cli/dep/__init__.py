# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ddev.cli.dep.freeze import freeze
from ddev.cli.dep.pin import pin
from ddev.cli.dep.sync import sync
from ddev.cli.dep.updates import updates


@click.group(short_help='Manage dependencies')
def dep():
    pass


dep.add_command(freeze)
dep.add_command(pin)
dep.add_command(sync)
dep.add_command(updates)
