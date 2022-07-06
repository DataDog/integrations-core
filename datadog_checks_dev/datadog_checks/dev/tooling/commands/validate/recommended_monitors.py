# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os

import click

from ....utils import read_file
from ...manifest_utils import Manifest
from ...testing import process_checks_option
from ...utils import complete_valid_checks, get_assets_from_manifest, get_manifest_file
from ..console import (
    CONTEXT_SETTINGS,
    abort,
    annotate_display_queue,
    annotate_error,
    echo_failure,
    echo_info,
    echo_success,
)

REQUIRED_ATTRIBUTES = {'name', 'type', 'query', 'message', 'tags', 'options', 'recommended_monitor_metadata'}
EXTRA_NOT_ALLOWED_FIELDS = ['id']
ALLOWED_MONITOR_TYPES = [
    'audit alert',
    'event alert',
    'event-v2 alert',
    'log alert',
    'query alert',
    'rum alert',
    'service check',
    'trace-analytics alert',
]


@click.command(
    'recommended-monitors',
    context_settings=CONTEXT_SETTINGS,
    short_help='Validate recommended monitor definition JSON files',
)
@click.argument('check', shell_complete=complete_valid_checks, required=False)
def recommended_monitors(check):
    """Validate all recommended monitors definition files.

    If `check` is specified, only the check will be validated, if check value is 'changed' will only apply to changed
    checks, an 'all' or empty `check` value will validate all README files.
    """

    checks = process_checks_option(check, source='integrations', extend_changed=True)
    echo_info(f"Validating recommended monitors for {len(checks)} checks ...")

    failed_checks = 0
    ok_checks = 0

    for check_name in checks:
        display_queue = []
        file_failed = False
        manifest = Manifest.load_manifest(check_name)
        monitors_relative_locations, invalid_files = get_assets_from_manifest(check_name, 'monitors')
        manifest_file = get_manifest_file(check_name)
        for file in invalid_files:
            echo_info(f'{check_name}... ', nl=False)
            echo_info(' FAILED')
            message = f'{file} does not exist'
            echo_failure('  ' + message)
            failed_checks += 1
            annotate_error(manifest_file, message)

        for monitor_file in monitors_relative_locations:
            monitor_filename = os.path.basename(monitor_file)
            try:
                decoded = json.loads(read_file(monitor_file).strip())
            except json.JSONDecodeError as e:
                failed_checks += 1
                echo_info(f'{check_name}... ', nl=False)
                echo_failure(' FAILED')
                message = f'invalid json: {e}'
                echo_failure('  ' + message)
                annotate_error(monitor_file, message)
                continue

            all_keys = set(decoded.keys())
            if not REQUIRED_ATTRIBUTES.issubset(all_keys):
                missing_fields = REQUIRED_ATTRIBUTES.difference(all_keys)
                file_failed = True
                display_queue.append(
                    (echo_failure, f"    {monitor_filename} does not contain the required fields: {missing_fields}"),
                )
            elif any([item for item in all_keys if item in EXTRA_NOT_ALLOWED_FIELDS]):
                file_failed = True
                display_queue.append(
                    (
                        echo_failure,
                        f"    {monitor_filename} contains unsupported field(s). Please ensure none of the following are"
                        f" in the file: {EXTRA_NOT_ALLOWED_FIELDS}",
                    ),
                )
            else:
                # If all required keys exist, validate value
                monitor_type = decoded.get('type')
                if monitor_type not in ALLOWED_MONITOR_TYPES:
                    file_failed = True
                    display_queue.append(
                        (
                            echo_failure,
                            f"    {monitor_filename} is of unsupported type: \"{monitor_type}\". Only"
                            f" the following types are allowed: {ALLOWED_MONITOR_TYPES}",
                        )
                    )

                description = decoded.get('recommended_monitor_metadata').get('description')
                if description is not None:
                    if len(description) > 300:
                        file_failed = True
                        display_queue.append(
                            (
                                echo_failure,
                                f"    {monitor_filename} has a description field that is too long, must be < 300 chars",
                            ),
                        )

                result = [i for i in decoded.get('tags') if i.startswith('integration:')]
                if len(result) < 1:
                    file_failed = True
                    display_queue.append((echo_failure, f"    {monitor_filename} must have an `integration` tag"))

                display_name = manifest.get_display_name().lower()
                monitor_name = decoded.get('name').lower()
                if not (check_name in monitor_name or display_name in monitor_name):
                    file_failed = True
                    if check_name == display_name:
                        error_msg = f":{check_name}"
                    else:
                        error_msg = f". Either: {check_name} or {display_name}"
                    display_queue.append(
                        (
                            echo_failure,
                            f"    {monitor_filename} `name` field must contain the integration name{error_msg}",
                        ),
                    )

            if file_failed:
                failed_checks += 1
                # Display detailed info if file is invalid
                echo_info(f'{check_name}... ', nl=False)
                echo_failure(' FAILED')
                annotate_display_queue(monitor_file, display_queue)
                for display_func, message in display_queue:
                    display_func(message)
                display_queue = []
            else:
                ok_checks += 1

    if ok_checks:
        echo_success(f"{ok_checks} valid files")
    if failed_checks:
        echo_failure(f"{failed_checks} invalid files")
        abort()
