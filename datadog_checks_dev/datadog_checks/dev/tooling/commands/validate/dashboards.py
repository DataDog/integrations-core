# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import click

from ....utils import file_exists, read_file
from ...utils import get_valid_integrations, get_assets_from_manifest
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success

REQUIRED_ATTRIBUTES = {"board_title", "description", "template_variables", "widgets"}
DASH_ONLY_FIELDS = {"layout_type", "title", "created_at"}
DASH_ONLY_WIDGET_FIELDS = {"definition", "layout"}


def _is_dash_format(payload):
    for field in DASH_ONLY_FIELDS:
        if field in payload:
            return True

    # Also checks if any specified widget in the dashboard defines a dash only field
    for widget in payload["widgets"]:
        for field in DASH_ONLY_WIDGET_FIELDS:
            if field in widget:
                return True
    return False


@click.command('dashboards', context_settings=CONTEXT_SETTINGS, short_help='Validate dashboard definition JSON files')
def dashboards():
    """Validate all Dashboard definition files."""
    echo_info("Validating all Dashboard definition files...")
    failed_checks = 0
    ok_checks = 0

    for check_name in sorted(get_valid_integrations()):
        display_queue = []
        file_failed = False

        dashboard_relative_locations, invalid_files = get_assets_from_manifest(check_name, 'dashboards')
        for invalid in invalid_files:
            echo_info(f'{check_name}... ', nl=False)
            echo_info(' FAILED')
            echo_failure(f'  {invalid} does not exist')

        for dashboard_file in dashboard_relative_locations:
            try:
                decoded = json.loads(read_file(dashboard_file).strip())
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
                    (echo_failure, f"    {dashboard_file} does not contain the required fields: {missing_fields}"),
                )

            # Confirm the dashboard payload comes from the old API for now
            if _is_dash_format(decoded):
                file_failed = True
                display_queue.append(
                    (
                        echo_failure,
                        f'    {dashboard_file} is using the new /dash payload format which isn\'t currently supported.'
                        ' Please use the format from the /screen or /time API endpoints instead.',
                    ),
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
