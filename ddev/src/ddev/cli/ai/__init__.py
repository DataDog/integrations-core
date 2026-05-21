# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import click

from ddev.cli.ai.generate_lab import generate_lab


@click.group(short_help='Run experimental AI workflows')
def ai():
    """Run experimental AI workflows."""


ai.add_command(generate_lab)
