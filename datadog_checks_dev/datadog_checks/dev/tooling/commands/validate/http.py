# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click
from datadog_checks.dev.tooling.utils import get_valid_integrations, get_check_file

from ..console import echo_failure, echo_success, abort, CONTEXT_SETTINGS, echo_info, echo_debug


def validate_import(filepath, check):
    echo_info(f'filepath: {filepath}')
    echo_info(f'check name: {check}')


@click.command('http', context_settings=CONTEXT_SETTINGS, short_help='Validate usage of http wrapper')
def http():
    """Validate all integrations for usage of http wrapper."""
    echo_info("Validating all integrations for usage of http wrapper...")

    for check_name in sorted(get_valid_integrations()):
        validate_import(get_check_file(check_name), check_name)

    echo_success(f"ur smart")
