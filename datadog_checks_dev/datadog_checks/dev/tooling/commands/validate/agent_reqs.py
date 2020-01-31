# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ....utils import read_file
from ...constants import AGENT_V5_ONLY, NOT_CHECKS, get_agent_release_requirements
from ...release import get_package_name
from ...utils import get_valid_checks, get_version_string, parse_agent_req_file
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_warning


@click.command(
    'agent-reqs',
    context_settings=CONTEXT_SETTINGS,
    short_help="Verify that the checks versions are in sync with the requirements-agent-release.txt file",
)
def agent_reqs():
    """Verify that the checks versions are in sync with the requirements-agent-release.txt file"""

    echo_info("Validating requirements-agent-release.txt...")
    agent_reqs_content = parse_agent_req_file(read_file(get_agent_release_requirements()))
    ok_checks = 0
    unreleased_checks = []
    failed_checks = 0
    for check_name in get_valid_checks():
        if check_name not in AGENT_V5_ONLY | NOT_CHECKS:
            package_name = get_package_name(check_name)
            check_version = get_version_string(check_name)
            pinned_version = agent_reqs_content.get(package_name)
            if package_name not in agent_reqs_content:
                unreleased_checks.append(check_name)
                echo_warning(f'{check_name} has not yet been released')
            elif check_version != pinned_version:
                failed_checks += 1
                echo_failure(f"{check_name} has version {check_version} but is pinned to {pinned_version}")
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
