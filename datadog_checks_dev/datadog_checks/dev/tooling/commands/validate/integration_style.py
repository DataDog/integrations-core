# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import click

from ...testing import process_checks_option
from ...utils import complete_valid_checks, get_check_files
from ..console import CONTEXT_SETTINGS, annotate_warning, echo_info, echo_warning


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Validate check style for python files')
@click.argument('check', shell_complete=complete_valid_checks, required=False)
@click.option('--verbose', '-v', is_flag=True, help='Verbose mode')
@click.pass_context
def integration_style(ctx, check, verbose):
    """Validate that check follows style guidelines.

    If `check` is specified, only the check will be validated, if check value is 'changed' will only apply to changed
    checks, an 'all' or empty `check` value will validate all README files.
    """
    checks = process_checks_option(check, source='integrations')
    echo_info(f"Validating integration style for {len(checks)} integrations...")

    for check_name in checks:
        files = get_check_files(check_name, include_tests=False)
        for file in files:
            validate_check_instance(check_name, file, verbose)


def validate_check_instance(check_name, file, verbose):
    """
    Warns when the integration check function contains the `instance` parameter.
    """
    with open(file, 'r', encoding='utf-8') as f:
        read_file = f.read()
        found_match_arg = re.search(r"def check\(self, instance\):", read_file)
        if found_match_arg and verbose:
            message = (
                "The instance argument in the `check()` function is going to be "
                "deprecated in Agent 8. Please use `self.instance` instead."
            )
            echo_warning(f"{check_name}: " + message)
            annotate_warning(file, message)
