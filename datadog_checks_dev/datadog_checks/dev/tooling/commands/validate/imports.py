# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import click

from ...testing import process_checks_option
from ...utils import complete_valid_checks, get_check_files
from ..console import CONTEXT_SETTINGS, abort, echo_debug, echo_failure, echo_info, echo_success, echo_warning


def validate_import(filepath, check, autofix):
    """Validate imports are coming from the correct base package."""
    # almost every case is of the form `from datadog_checks.. import ..`
    # we want to ensure that the imports are from `datadog_checks.base...`
    # except for cases where its importing from actual check code

    success = True
    lines = []

    with open(filepath) as f:
        for num, line in enumerate(f):
            if all(
                (
                    'import' in line,
                    'datadog_checks' in line,
                    'datadog_checks.base' not in line,
                    f'datadog_checks.{check}' not in line,
                    'datadog_checks.dev' not in line,
                )
            ):
                success = False
                lines.append((num, line))

    if autofix and not success:
        with open(filepath, 'r') as f:
            data = f.readlines()

        for num, _ in lines:
            data[num] = data[num].replace('datadog_checks', 'datadog_checks.base')

        with open(filepath, 'w') as f:
            f.write(''.join(data))

    return success, lines


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Validate proper base imports')
@click.argument('check', autocompletion=complete_valid_checks, required=False)
@click.option('--autofix', is_flag=True, help='Apply suggested fix')
@click.pass_context
def imports(ctx, check, autofix):
    """Validate proper imports in checks.

    If `check` is specified, only the check will be validated, if check value is 'changed' will only apply to changed
    checks, an 'all' or empty `check` value will validate all README files.
    """

    validation_fails = {}

    checks = process_checks_option(check, source='integrations')
    echo_info(f"Validating imports for {len(checks)} checks to avoid deprecated modules ...")

    for check_name in checks:
        echo_debug(f'Checking {check_name}')

        # focus on check and testing directories
        for fpath in get_check_files(check_name):
            success, lines = validate_import(fpath, check_name, autofix)

            if not success:
                validation_fails[fpath] = lines

    if validation_fails:
        num_files = len(validation_fails)
        num_failures = sum(len(lines) for lines in validation_fails.values())
        echo_failure(f'\nValidation failed: {num_failures} deprecated imports found in {num_files} files:\n')
        for f, lines in validation_fails.items():
            for line in lines:
                linenum, linetext = line
                echo_warning(f'{f}: line # {linenum}', indent='  ')
                echo_info(f'{linetext}', indent='    ')

        abort()

    else:
        echo_success('Validation passed!')
