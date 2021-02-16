# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os

import click

from ....utils import read_file
from ...utils import get_assets_from_manifest, get_valid_integrations, load_manifest
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success

REQUIRED_ATTRIBUTES = {'name', 'type', 'query', 'message', 'tags', 'options', 'recommended_monitor_metadata'}
EXTRA_NOT_ALLOWED_FIELDS = ['id']
ALLOWED_MONITOR_TYPES = ['query alert', 'event alert', 'service check']


@click.command(
    'recommended-monitors',
    context_settings=CONTEXT_SETTINGS,
    short_help='Validate recommended monitor definition JSON files',
)
def recommended_monitors():
    """Validate all recommended monitors definition files."""
    echo_info("Validating all recommended monitors...")
    failed_checks = 0
    ok_checks = 0

    for check_name in sorted(get_valid_integrations()):
        display_queue = []
        file_failed = False
        manifest = load_manifest(check_name)
        monitors_relative_locations, invalid_files = get_assets_from_manifest(check_name, 'monitors')
        for file in invalid_files:
            echo_info(f'{check_name}... ', nl=False)
            echo_info(' FAILED')
            echo_failure(f'  {file} does not exist')
            failed_checks += 1

        for monitor_file in monitors_relative_locations:
            monitor_filename = os.path.basename(monitor_file)
            try:
                decoded = json.loads(read_file(monitor_file).strip())
            except json.JSONDecodeError as e:
                failed_checks += 1
                echo_info(f'{check_name}... ', nl=False)
                echo_failure(' FAILED')
                echo_failure(f'  invalid json: {e}')
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
                # If all required keys exist, validate values

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

                display_name = manifest.get("display_name").lower()
                monitor_name = decoded.get('name').lower()
                if not (check_name in monitor_name or display_name in monitor_name):
                    file_failed = True
                    display_queue.append(
                        (echo_failure, f"    {monitor_filename} name must contain the integration name"),
                    )

        if file_failed:
            failed_checks += 1
            # Display detailed info if file is invalid
            echo_info(f'{check_name}... ', nl=False)
            echo_failure(' FAILED')
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
