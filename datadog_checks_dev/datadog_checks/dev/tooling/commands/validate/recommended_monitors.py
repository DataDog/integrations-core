# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os

import click

from ....utils import file_exists, read_file
from ...constants import get_root
from ...utils import get_valid_integrations, load_manifest
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success

REQUIRED_ATTRIBUTES = {'name', 'type', 'query', 'message', 'tags', 'options', 'recommended_monitor_metadata'}

## Questions
## 1 monitor per file


@click.command('recommended-monitors', context_settings=CONTEXT_SETTINGS, short_help='Validate recommended monitor definition JSON files')
def recommended_monitors():
    """Validate all recommended monitors definition files."""
    root = get_root()
    echo_info("Validating all recommended monitors...")
    failed_checks = 0
    ok_checks = 0

    for check_name in sorted(get_valid_integrations()):
        display_queue = []
        file_failed = False
        manifest = load_manifest(check_name)
        monitors_relative_locations = manifest.get('assets', {}).get('monitors', {}).values()
        for monitor_relative_location in monitors_relative_locations:

            monitor_file = os.path.join(root, check_name, *monitor_relative_location.split('/'))
            if not file_exists(monitor_file):
                echo_info(f'{check_name}... ', nl=False)
                echo_info(' FAILED')
                echo_failure(f'  {monitor_file} does not exist')
                failed_checks += 1
                continue

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
                    (echo_failure, f"    {monitor_file} does not contain the required fields: {missing_fields}"),
                )
            else:
                if decoded.get(decoded.get('recommended_monitor_metadata').get('description')) is not None:
                    if len(decoded.get(decoded.get('recommended_monitor_metadata').get('description'))) < 300:
                        file_failed = True
                        display_queue.append(
                            (echo_failure, f"    {monitor_file} has a description field that is too long, must be <300 chars"),
                        )

                # if decoded.get('tags'):

            if file_failed:
                failed_checks += 1
                # Display detailed info if file is invalid
                echo_info(f'{check_name}... ', nl=False)
                echo_failure(' FAILED')
                for display_func, message in display_queue:
                    display_func(message)
            else:
                ok_checks += 1

    if ok_checks:
        echo_success(f"{ok_checks} valid files")
    if failed_checks:
        echo_failure(f"{failed_checks} invalid files")
        abort()
