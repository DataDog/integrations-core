# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import click

from ....utils import read_file
from ...annotations import annotate_display_queue, annotate_error
from ...testing import process_checks_option
from ...utils import complete_valid_checks, get_assets_from_manifest, get_manifest_file
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success

REQUIRED_ATTRIBUTES = {"description", "template_variables", "widgets"}
DASHBOARD_ONLY_FIELDS = {"layout_type", "title", "created_at"}
DASHBOARD_ONLY_WIDGET_FIELDS = {"definition", "layout"}


def _is_dashboard_format(payload):
    for field in DASHBOARD_ONLY_FIELDS:
        if field in payload:
            return True

    # Also checks if any specified widget in the dashboard defines a dash only field
    for widget in payload["widgets"]:
        for field in DASHBOARD_ONLY_WIDGET_FIELDS:
            if field in widget:
                return True
    return False


@click.command('dashboards', context_settings=CONTEXT_SETTINGS, short_help='Validate dashboard definition JSON files')
@click.argument('check', autocompletion=complete_valid_checks, required=False)
def dashboards(check):
    """Validate all Dashboard definition files.

    If `check` is specified, only the check will be validated, if check value is 'changed' will only apply to changed
    checks, an 'all' or empty `check` value will validate all README files.
    """
    failed_checks = 0
    ok_checks = 0

    checks = process_checks_option(check, source='integrations')
    echo_info(f"Validating Dashboard definition files for {len(checks)} checks...")

    for check_name in checks:
        display_queue = []
        file_failed = False

        dashboard_relative_locations, invalid_files = get_assets_from_manifest(check_name, 'dashboards')
        manifest_file = get_manifest_file(check_name)
        for invalid in invalid_files:
            message = f'{invalid} does not exist'
            echo_info(f'{check_name}... ', nl=False)
            echo_info(' FAILED')
            echo_failure('  ' + message)
            failed_checks += 1
            annotate_error(manifest_file, message)

        for dashboard_file in dashboard_relative_locations:
            dashboard_filename = os.path.basename(dashboard_file)
            try:
                decoded = json.loads(read_file(dashboard_file).strip())
            except json.JSONDecodeError as e:
                failed_checks += 1
                message = f'invalid json: {e}'
                echo_info(f'{check_name}... ', nl=False)
                echo_failure(' FAILED')
                echo_failure('  ' + message)
                annotate_error(dashboard_file, message)
                continue

            all_keys = set(decoded.keys())
            if not REQUIRED_ATTRIBUTES.issubset(all_keys):
                missing_fields = REQUIRED_ATTRIBUTES.difference(all_keys)
                file_failed = True
                display_queue.append(
                    (
                        echo_failure,
                        f"    {dashboard_filename} does not contain the required fields: "
                        f"{', '.join(sorted(missing_fields))}",
                    ),
                )

            # Confirm the dashboard payload comes from the old API for now
            if not _is_dashboard_format(decoded):
                file_failed = True
                display_queue.append(
                    (echo_failure, f'    {dashboard_filename} is not using the new /dashboard payload format.'),
                )

            if file_failed:
                failed_checks += 1
                # Display detailed info if file is invalid
                echo_info(f'{check_name}... ', nl=False)
                echo_failure(' FAILED')
                annotate_display_queue(dashboard_file, display_queue)
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
