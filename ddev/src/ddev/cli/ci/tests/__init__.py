# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ddev.cli.ci.tests.validate_inputs import validate_inputs


@click.group(short_help='Dispatcher test run utilities')
def tests():
    """Utilities for the Dispatcher's test runs."""


tests.add_command(validate_inputs)
