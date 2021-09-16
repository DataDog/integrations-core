# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ....utils import read_file
from ...annotations import annotate_error
from ...constants import AGENT_V5_ONLY, NOT_CHECKS, get_agent_release_requirements
from ...release import get_package_name
from ...testing import process_checks_option
from ...utils import complete_valid_checks, get_version_string, parse_agent_req_file
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_warning


@click.command(
    'agent-reqs',
    context_settings=CONTEXT_SETTINGS,
    short_help="Verify that the checks versions are in sync with the requirements-agent-release.txt file",
)
@click.argument('check', autocompletion=complete_valid_checks, required=False)
def agent_reqs(check):
    """Verify that the checks versions are in sync with the requirements-agent-release.txt file.

    If `check` is specified, only the check will be validated, if check value is 'changed' will only apply to changed
    checks, an 'all' or empty `check` value will validate all README files.
    """

    echo_info("Validating requirements-agent-release.txt...")
    release_requirements_file = get_agent_release_requirements()
    agent_reqs_content = parse_agent_req_file(read_file(release_requirements_file))
    ok_checks = 0
    unreleased_checks = []
    failed_checks = 0

    checks = process_checks_option(check)

    for check_name in checks:
        if check_name not in AGENT_V5_ONLY | NOT_CHECKS:
            package_name = get_package_name(check_name)
            check_version = get_version_string(check_name)
            pinned_version = agent_reqs_content.get(package_name)
            if package_name not in agent_reqs_content:
                unreleased_checks.append(check_name)
                message = f'{check_name} has not yet been released'
                echo_warning(message)
            elif check_version != pinned_version:
                failed_checks += 1
                message = f"{check_name} has version {check_version} but is pinned to {pinned_version}"
                echo_failure(message)
                annotate_error(release_requirements_file, message)
            else:
                ok_checks += 1

    if ok_checks:
        echo_success(f"{ok_checks} correctly pinned checks")
    if unreleased_checks:
        joined_checks = ', '.join(unreleased_checks)
        echo_warning(f"{len(unreleased_checks)} unreleased checks: {joined_checks}")
    if failed_checks:
        echo_failure(f"{failed_checks} checks out of sync")
        abort()
