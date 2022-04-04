# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import click

from ....fs import basepath
from ...testing import process_checks_option
from ...utils import (
    complete_valid_checks,
    get_package_name,
    get_project_file,
    get_setup_file,
    has_project_file,
    load_project_file_cached,
    normalize_package_name,
    normalize_project_name,
    read_setup_file,
)
from ..console import CONTEXT_SETTINGS, abort, annotate_display_queue, echo_failure, echo_info, echo_success

# Some integrations aren't installable via the integration install command, so exclude them from the name requirements
EXCLUDE_CHECKS = ["datadog_checks_downloader", "datadog_checks_dev", "datadog_checks_base"]


def read_project_name(check_name):
    if has_project_file(check_name):
        return get_project_file(check_name), load_project_file_cached(check_name)['project']['name']

    lines = read_setup_file(check_name)
    for _, line in lines:
        match = re.search("name=['\"](.*)['\"]", line)
        if match:
            return get_setup_file(check_name), match.group(1)


@click.command('package', context_settings=CONTEXT_SETTINGS, short_help='Validate Python package metadata')
@click.argument('check', shell_complete=complete_valid_checks, required=False)
def package(check):
    """Validate all files for Python package metadata.

    If `check` is specified, only the check will be validated, if check value is 'changed' will only apply to changed
    checks, an 'all' or empty `check` value will validate all files.
    """

    checks = process_checks_option(check, source='valid_checks', validate=True)
    echo_info(f'Validating files for {len(checks)} checks ...')

    failed_checks = 0
    ok_checks = 0

    for check in checks:
        display_queue = []
        file_failed = False
        if check in EXCLUDE_CHECKS:
            continue

        source, project_name = read_project_name(check)
        normalization_function = normalize_project_name if has_project_file(check) else normalize_package_name
        project_name = normalization_function(project_name)
        normalized_project_name = normalization_function(f'datadog-{check}')
        # The name field must match the pattern: `datadog-<folder_name>`
        if project_name != normalized_project_name:
            file_failed = True
            display_queue.append(
                (
                    echo_failure,
                    f'    The name in {basepath(source)}: {project_name} must be: `{normalized_project_name}`',
                )
            )

        if has_project_file(check):
            project_data = load_project_file_cached(check)
            version_file = project_data.get('tool', {}).get('hatch', {}).get('version', {}).get('path', '')
            expected_version_file = f'datadog_checks/{get_package_name(check)}/__about__.py'
            if version_file != expected_version_file:
                file_failed = True
                display_queue.append(
                    (
                        echo_failure,
                        f'    The field `tool.hatch.version.path` in {check}/pyproject.toml '
                        f'must be set to: {expected_version_file}',
                    )
                )

        if file_failed:
            failed_checks += 1
            # Display detailed info if file is invalid
            echo_info(f'{check}... ', nl=False)
            echo_failure(' FAILED')
            annotate_display_queue(source, display_queue)
            for display_func, message in display_queue:
                display_func(message)
        else:
            ok_checks += 1

    if ok_checks:
        echo_success(f"{ok_checks} valid files")
    if failed_checks:
        echo_failure(f"{failed_checks} invalid files")
        abort()
