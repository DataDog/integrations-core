# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import click

from ...utils import complete_valid_checks, find_legacy_signature, get_valid_checks
from ..console import CONTEXT_SETTINGS, echo_failure, echo_success


@click.command(
    'legacy-signature',
    context_settings=CONTEXT_SETTINGS,
    short_help='Validate that no integration uses the legacy signature',
)
@click.argument('check', autocompletion=complete_valid_checks, required=False)
def legacy_signature(check):
    """Validate that no integration uses the legacy signature."""
    if check:
        checks = [check]
    else:
        checks = sorted(get_valid_checks())

    has_failed = False

    for check in checks:
        check_failed = find_legacy_signature(check)
        if check_failed is not None:
            has_failed = True
            failed_file, failed_num = check_failed
            echo_failure(f"Check `{check}` uses legacy agent signature in `{failed_file}` on line {failed_num}")

    if not has_failed:
        if check:
            echo_success(f"Check `{check}` uses the new agent signature.")
        else:
            echo_success('All checks use the new agent signature.')
    return
