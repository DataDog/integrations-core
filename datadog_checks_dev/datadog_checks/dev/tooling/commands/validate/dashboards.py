# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import click

from ....fs import write_file
from ....utils import read_file
from ...annotations import annotate_display_queue, annotate_error
from ...manifest_utils import Manifest
from ...testing import process_checks_option
from ...utils import complete_valid_checks, get_assets_from_manifest, get_manifest_file
from ..console import CONTEXT_SETTINGS, abort, echo_debug, echo_failure, echo_info, echo_success

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


def check_widgets(decoded, filename, app_uuid, fix, file_fixed, file_failed, display_queue):
    """Recursively check the decoded dashboard object for widget references and validate the app_id inside."""
    for widget in decoded.get('widgets', []):

        if widget.get('definition', {}).get('widgets'):
            decoded = {'widgets': widget['definition']['widgets']}
            file_fixed, file_failed = check_widgets(
                decoded, filename, app_uuid, fix, file_fixed, file_failed, display_queue
            )

        widget_app_uuid = widget.get('definition', {}).get('app_id')
        if widget_app_uuid and widget_app_uuid != app_uuid:
            if fix:
                widget['definition']['app_id'] = app_uuid
                file_fixed = True
                continue
            else:
                file_failed = True
                msg = (
                    f"    {filename} widget {widget['id']} does not contain correct app_uuid: "
                    f"{widget_app_uuid} should be {app_uuid}"
                )
                display_queue.append(
                    (echo_failure, msg),
                )
    return file_fixed, file_failed


@click.command('dashboards', context_settings=CONTEXT_SETTINGS, short_help='Validate dashboard definition JSON files')
@click.argument('check', autocompletion=complete_valid_checks, required=False)
@click.option('--fix', is_flag=True, help='Attempt to fix errors')
def dashboards(check, fix):
    """Validate all Dashboard definition files.

    If `check` is specified, only the check will be validated, if check value is 'changed' will only apply to changed
    checks, an 'all' or empty `check` value will validate all README files.
    """
    failed_checks = 0
    ok_checks = 0

    checks = process_checks_option(check, source='integrations')
    echo_info(f"Validating Dashboard definition files for {len(checks)} checks...")

    for check_name in checks:
        echo_debug(f"Validating Dashboard definition files for {check_name} check...")
        display_queue = []
        file_failed = False
        file_fixed = False

        manifest = Manifest.load_manifest(check_name)
        manifest_file = get_manifest_file(check_name)

        dashboard_relative_locations, invalid_files = get_assets_from_manifest(check_name, 'dashboards')
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

            # check app_id for Manifest V2 dashboards
            if manifest.version == Manifest.V2:
                echo_debug(f'Validating app dashboard {dashboard_filename} ..')
                app_uuid = manifest.get_app_uuid()

                file_fixed, file_failed = check_widgets(
                    decoded, dashboard_filename, app_uuid, fix, file_fixed, file_failed, display_queue
                )

            if fix and file_fixed:
                new_dashboard = f"{json.dumps(decoded, indent=2, separators=(',', ': '))}\n"
                write_file(dashboard_file, new_dashboard)
                echo_info(f"{dashboard_file}... ", nl=False)
                echo_success("FIXED")

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
