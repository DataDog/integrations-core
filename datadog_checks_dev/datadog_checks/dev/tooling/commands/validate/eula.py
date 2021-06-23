# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ...testing import process_checks_option
from ...utils import complete_valid_checks, get_eula_from_manifest
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success


@click.command('eula', context_settings=CONTEXT_SETTINGS, short_help='Validate EULA files')
@click.argument('check', autocompletion=complete_valid_checks, required=False)
def eula(check):
    """Validate all EULA definition files.

    If `check` is specified, only the check will be validated, if check value is 'changed' will only apply to changed
    checks, an 'all' or empty `check` value will validate all README files.
    """
    echo_info("Validating all EULA files...")
    failed_checks = 0
    ok_checks = 0

    checks = process_checks_option(check, source='integrations')
    echo_info(f"Validating EULA files for {len(checks)} checks...")

    for check_name in checks:
        eula_relative_location, eula_exists = get_eula_from_manifest(check_name)

        if not eula_exists:
            echo_info(f'{check_name}... ', nl=False)
            echo_info(' FAILED')
            echo_failure(f'  {eula_relative_location} does not exist')
            failed_checks += 1
            continue

        # Check file extension of eula is .pdf
        if not eula_relative_location.endswith(".pdf"):
            echo_info(f'{check_name}... ', nl=False)
            echo_info(' FAILED')
            echo_failure(f'  {eula_relative_location} is missing the pdf extension')
            continue

        # Check PDF starts with PDF magic_number: "%PDF"
        with open(eula_relative_location, 'rb') as f:
            magic_number = f.readline()
            if b'%PDF' not in magic_number:
                echo_info(f'{check_name}... ', nl=False)
                echo_info(' FAILED')
                echo_failure(f'  {eula_relative_location} is not a PDF file')
                failed_checks += 1
                continue

        ok_checks += 1

    if ok_checks:
        echo_success(f"{ok_checks} valid files")
    if failed_checks:
        echo_failure(f"{failed_checks} invalid files")
        abort()
