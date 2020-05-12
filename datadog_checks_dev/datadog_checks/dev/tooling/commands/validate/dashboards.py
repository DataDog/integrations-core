# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import click

from ....utils import file_exists, read_file
from ...constants import get_root
from ...utils import get_valid_integrations, load_manifest
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success

REQUIRED_ATTRIBUTES = {'agent_version', 'check', 'description', 'groups', 'integration', 'name', 'statuses'}


@click.command('dashboards', context_settings=CONTEXT_SETTINGS, short_help='Validate dashboard definition JSON files')
def dashboards():
    """Validate all Dashboard definition files."""
    root = get_root()
    echo_info("Validating all Dashboard definition files...")
    failed_checks = 0
    ok_checks = 0

    for check_name in sorted(get_valid_integrations()):
        display_queue = []
        file_failed = False
        manifest = load_manifest(check_name)
        dashboard_relative_locations = manifest.get('assets', {}).get('dashboards', {}).values()

        for dashboard_relative_location in dashboard_relative_locations:

            dashboard_file = os.path.join(root, check_name, *dashboard_relative_location.split('/'))
            if not file_exists(dashboard_file):
                echo_info(f'{check_name}... ', nl=False)
                echo_info(' FAILED')
                echo_failure(f'  {dashboard_file} does not exist')
                failed_checks += 1
                continue

            try:
                decoded = json.loads(read_file(dashboard_file).strip())
            except json.JSONDecodeError as e:
                failed_checks += 1
                echo_info(f'{check_name}... ', nl=False)
                echo_failure(' FAILED')
                echo_failure(f'  invalid json: {e}')
                continue

            # Confirm the dashboard payload comes from the old API for now
            if 'layout_type' in decoded:
                file_failed = True
                display_queue.append(
                    (
                        echo_failure,
                        '    {} is using the new /dash payload format which isn\'t currently supported.'
                        ' Please use the format from the /screen or /time API endpoints instead.'.format(
                            dashboard_file
                        ),
                    )
                )

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
