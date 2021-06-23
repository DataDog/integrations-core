# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import click

from ...testing import process_checks_option
from ...utils import complete_valid_checks, normalize_package_name, read_setup_file
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success

# Some integrations aren't installable via the integration install command, so exclude them from the name requirements
EXCLUDE_CHECKS = ["datadog_checks_downloader", "datadog_checks_dev", "datadog_checks_base"]


@click.command('package', context_settings=CONTEXT_SETTINGS, short_help='Validate `setup.py` files')
@click.argument('check', autocompletion=complete_valid_checks, required=False)
def package(check):
    """Validate all `setup.py` files.

    If `check` is specified, only the check will be validated, if check value is 'changed' will only apply to changed
    checks, an 'all' or empty `check` value will validate all README files.
    """

    checks = process_checks_option(check, source='valid_checks', validate=True)
    echo_info(f"Validating setup.py files for {len(checks)} checks ...")

    failed_checks = 0
    ok_checks = 0

    for check in checks:
        display_queue = []
        file_failed = False

        if check in EXCLUDE_CHECKS:
            continue

        lines = read_setup_file(check)
        for _, line in lines:
            # The name field must match the pattern: `datadog-<folder_name>`
            match = re.search("name=['\"](.*)['\"]", line)
            if match:
                group = match.group(1)
                # Following PEP 503, lets normalize the groups and validate those
                # https://www.python.org/dev/peps/pep-0503/#normalized-names
                group = normalize_package_name(group)
                normalized_package_name = normalize_package_name(f"datadog-{check}")
                if group != normalized_package_name:
                    file_failed = True
                    display_queue.append(
                        (echo_failure, f"    The name in setup.py: {group} must be: `{normalized_package_name}`")
                    )

        if file_failed:
            failed_checks += 1
            # Display detailed info if file is invalid
            echo_info(f'{check}... ', nl=False)
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
