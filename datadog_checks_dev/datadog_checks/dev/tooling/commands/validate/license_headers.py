# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pathlib

import click

from ...constants import get_root
from ...license_headers import validate_license_headers
from ...testing import process_checks_option
from ...utils import complete_valid_checks
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success

IGNORES = {"datadog_checks_dev": ["datadog_checks/dev/tooling/templates"]}


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Validate license headers in python files')
@click.argument('check', shell_complete=complete_valid_checks, required=False)
@click.pass_context
def license_headers(ctx, check):
    """Validate license headers in python code files.

    If `check` is specified, only the check will be validated, if check value is 'changed' will only apply to changed
    checks, an 'all' or empty `check` value will validate all python files.
    """
    root = pathlib.Path(get_root())
    is_extras = ctx.obj['repo_choice'] == 'extras'
    is_marketplace = ctx.obj['repo_choice'] == 'marketplace'

    if is_extras or is_marketplace:
        echo_info('License header validation is not implemented for `extras` or `marketplace`.')
        return

    checks = process_checks_option(check, source='integrations')

    total_errors = 0

    for check_name in checks:
        path_to_check = root / check_name
        ignores = [pathlib.Path(p) for p in IGNORES.get(check_name, [])]
        errors = validate_license_headers(path_to_check, extra_ignore=ignores)

        for err in errors:
            echo_failure(f'{check_name}/{err.path}: {err.message}')
            total_errors += 1

    if total_errors:
        echo_failure(f'Found {total_errors} files with errors.')
        abort()
    else:
        echo_success('All license headers are valid.')
