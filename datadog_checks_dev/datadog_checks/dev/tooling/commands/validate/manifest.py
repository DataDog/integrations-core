# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import click

from ....fs import file_exists, read_file, write_file
from ...annotations import annotate_display_queue, annotate_error
from ...constants import get_root
from ...datastructures import JSONDict
from ...manifest_validator import get_all_validators
from ...manifest_validator.constants import V1_STRING
from ...testing import process_checks_option
from ...utils import complete_valid_checks
from ..console import CONTEXT_SETTINGS, abort, echo_debug, echo_failure, echo_info, echo_success, echo_warning


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Validate `manifest.json` files')
@click.argument('check', autocompletion=complete_valid_checks, required=False)
@click.option('--fix', is_flag=True, help='Attempt to fix errors')
@click.pass_context
def manifest(ctx, check, fix):
    """Validate `manifest.json` files.

    If `check` is specified, only the check will be validated, if check value is 'changed' will only apply to changed
    checks, an 'all' or empty `check` value will validate all README files.
    """
    root = get_root()
    is_extras = ctx.obj['repo_choice'] == 'extras'
    is_marketplace = ctx.obj['repo_choice'] == 'marketplace'
    ok_checks = 0
    failed_checks = 0
    fixed_checks = 0
    message_methods = {'success': echo_success, 'warning': echo_warning, 'failure': echo_failure, 'info': echo_info}

    checks = process_checks_option(check, source='integrations')
    echo_info(f"Validating manifest.json files for {len(checks)} checks ...")

    for check_name in checks:
        echo_debug(f"Validating manifest.json files for {check_name} ...")

        manifest_file = os.path.join(root, check_name, 'manifest.json')

        if file_exists(manifest_file):
            display_queue = []
            file_failures = 0
            file_fixed = False

            try:
                decoded = json.loads(read_file(manifest_file).strip())
                decoded = JSONDict(decoded)
            except json.JSONDecodeError as e:
                failed_checks += 1
                echo_info(f"{check_name}/manifest.json... ", nl=False)
                echo_failure("FAILED")
                echo_failure(f'  invalid json: {e}')
                annotate_error(manifest_file, f"Invalid json: {e}")
                continue

            version = decoded.get('manifest_version', V1_STRING)
            all_validators = get_all_validators(ctx, version, is_extras, is_marketplace)

            for validator in all_validators:
                if validator.skip_if_errors and file_failures > 0:
                    echo_info(f'Skipping validation {validator} since errors have already been found.')
                    continue
                validator.validate(check_name, decoded, fix)
                file_failures += 1 if validator.result.failed else 0
                file_fixed += 1 if validator.result.fixed else 0
                for msg_type, messages in validator.result.messages.items():
                    for message in messages:
                        display_queue.append((message_methods[msg_type], message))

            if file_failures > 0:
                failed_checks += 1
                # Display detailed info if file invalid
                echo_info(f"{check_name}/manifest.json... ", nl=False)
                echo_failure("FAILED")
                annotate_display_queue(manifest_file, display_queue)
                for display_func, message in display_queue:
                    display_func(message)
            elif not file_fixed:
                ok_checks += 1

            if fix and file_fixed:
                new_manifest = f"{json.dumps(decoded, indent=2, separators=(',', ': '))}\n"
                write_file(manifest_file, new_manifest)
                # Display detailed info if file has been completely fixed
                if file_failures == 0:
                    fixed_checks += 1
                    echo_info(f"{check_name}/manifest.json... ", nl=False)
                    echo_success("FIXED")
                    for display_func, message in display_queue:
                        display_func(message)

    if ok_checks:
        echo_success(f"{ok_checks} valid files")
    if fixed_checks:
        echo_info(f"{fixed_checks} fixed files")
    if failed_checks:
        echo_failure(f"{failed_checks} invalid files")
        abort()
