# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import glob
import os
import re
import sys
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor
from email.errors import InvalidHeaderDefect
from email.headerregistry import Address

import click
from datadog_checks.dev import run_command
from datadog_checks.dev.fs import basepath
from datadog_checks.dev.tooling.commands.console import (
    CONTEXT_SETTINGS,
    abort,
    annotate_display_queue,
    echo_failure,
    echo_info,
    echo_success,
)
from datadog_checks.dev.tooling.testing import process_checks_option
from datadog_checks.dev.tooling.utils import (
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

# Some integrations aren't installable via the integration install command, so exclude them from the name requirements
EXCLUDE_CHECKS = ["datadog_checks_downloader", "datadog_checks_dev", "datadog_checks_base", "ddev"]

ALLOWED_DIST_INFO_FILES = frozenset(
    {
        'DESCRIPTION.rst',
        'METADATA',
        'RECORD',
        'WHEEL',
        'entry_points.txt',
        'metadata.json',
        'top_level.txt',
    }
)


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

    buildable_checks = [c for c in checks if c not in EXCLUDE_CHECKS]
    wheels = {}
    if buildable_checks:
        with ThreadPoolExecutor(max_workers=16) as executor:
            built = executor.map(_validate_wheel_contents, (read_project_name(c)[0] for c in buildable_checks))
            wheels = dict(zip(buildable_checks, built))

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

            # The emails of the authors must be valid
            invalid_emails = _validate_emails(check)
            if invalid_emails:
                file_failed = True
                display_queue.append(
                    (
                        echo_failure,
                        f'   Invalid email(s) found in {check}/pyproject.toml: {", ".join(invalid_emails)}.',
                    )
                )

        wheel_errors = wheels.get(check, [])
        if wheel_errors:
            file_failed = True
            display_queue.extend((echo_failure, error) for error in wheel_errors)

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


def _validate_wheel_contents(project_file):
    """Verify the wheel built the same way as the wheels pipeline only contains files its in-toto root
    layouts (e.g. `1.extras.root.layout`) allow: `datadog_checks/*` plus `ALLOWED_DIST_INFO_FILES` in the
    `*.dist-info` directory, e.g. a `LICENSE` the build backend embeds as `*.dist-info/licenses/LICENSE`
    would fail verification at release time.
    """
    with tempfile.TemporaryDirectory() as wheel_dir:
        result = run_command(
            [
                sys.executable,
                '-m',
                'pip',
                'wheel',
                os.path.dirname(project_file),
                '--ignore-requires-python',
                '--no-deps',
                f'--wheel-dir={wheel_dir}',
            ],
            capture=True,
        )
        if result.code != 0:
            return [f'    Could not build the wheel: {result.stderr or result.stdout}']

        wheels = glob.glob(os.path.join(wheel_dir, '*.whl'))
        if len(wheels) != 1:
            return [f'    Expected exactly one wheel from the build, found: {wheels}']

        errors = []
        with zipfile.ZipFile(wheels[0]) as wheel:
            for path in wheel.namelist():
                if path.endswith('/'):
                    continue
                top_level, _, file_name = path.partition('/')
                if top_level == 'datadog_checks' or (
                    top_level.endswith('.dist-info') and file_name in ALLOWED_DIST_INFO_FILES
                ):
                    continue
                errors.append(f'    Unexpected file in wheel: {path}')
        return errors


def _validate_emails(check_name):
    """
    Returns a list of invalid emails in the check's authors
    """
    if not has_project_file(check_name):
        return []

    authors = load_project_file_cached(check_name)['project']['authors']

    invalid_emails = []
    for author in authors:
        if 'email' in author:
            try:
                Address(addr_spec=author['email'])
            except InvalidHeaderDefect:
                invalid_emails.append(author['email'])

    return invalid_emails
