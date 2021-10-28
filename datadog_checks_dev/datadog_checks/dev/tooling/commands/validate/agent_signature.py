# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import click

from datadog_checks.dev.tooling.annotations import annotate_error

from ...testing import process_checks_option
from ...utils import complete_valid_checks, find_legacy_signature
from ..console import CONTEXT_SETTINGS, echo_failure, echo_success


@click.command(
    'legacy-signature',
    context_settings=CONTEXT_SETTINGS,
    short_help='Validate that no integration uses the legacy signature',
)
@click.argument('check', autocompletion=complete_valid_checks, required=False)
def legacy_signature(check):
    """Validate that no integration uses the legacy signature.

    If `check` is specified, only the check will be validated, if check value is 'changed' will only apply to changed
    checks, an 'all' or empty `check` value will validate all README files.
    """
    checks = process_checks_option(check)

    has_failed = False

    for check in checks:
        check_failed = find_legacy_signature(check)
        if check_failed is not None:
            has_failed = True
            failed_file_path, failed_num = check_failed
            failed_file = os.path.basename(failed_file_path)
            echo_failure(f"Check `{check}` uses legacy agent signature in `{failed_file}` on line {failed_num}")
            annotate_error(
                failed_file_path,
                "Detected use of legacy agent signature, please use the new signature",
                line=failed_num,
            )

    if not has_failed:
        if check:
            echo_success(f"Check `{check}` uses the new agent signature.")
        else:
            echo_success('All checks use the new agent signature.')
    return
