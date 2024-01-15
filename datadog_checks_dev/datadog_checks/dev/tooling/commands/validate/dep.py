# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import click
from packaging.requirements import Requirement

from ....utils import get_next
from ...constants import get_agent_requirements, get_root
from ...dependencies import (
    get_dependency_set,
    read_agent_dependencies,
    read_check_base_dependencies,
    read_check_dependencies,
)
from ...testing import process_checks_option
from ...utils import complete_valid_checks, get_project_file, has_project_file
from ..console import CONTEXT_SETTINGS, abort, annotate_error, annotate_errors, echo_failure, echo_success


def get_marker_string(dependency_definition):
    marker = dependency_definition.requirement.marker
    if marker is None:
        return '<N/A>'

    return str(marker)


def format_check_usage(checks, default=None):
    if not checks:
        return default

    checks = sorted(checks)
    num_checks = len(checks)
    if num_checks == 1:
        return checks[0]
    elif num_checks == 2:
        return f'{checks[0]} and {checks[1]}'
    else:
        remaining = num_checks - 2
        plurality = 's' if remaining > 1 else ''
        return f'{checks[0]}, {checks[1]}, and {remaining} other{plurality}'


def verify_base_dependency(source, check_name, dependency, force_pinned=True, min_base_version=None):
    """Minimal dependency verification for `datadog-checks-base` dependencies.

    Ensures that the version isn't specifically pinned since that will limit check installations.
    Optionally ensures that dependencies which have no pins are reported as errors.
    Optionally validate a specific version satisfies the base requirement spec.
    """
    failed = False
    name = 'datadog-checks-base'
    checks = [check_name]
    requirement = Requirement(dependency)
    specifier_set = requirement.specifier
    if has_project_file(check_name):
        file = get_project_file(check_name)
    else:
        file = os.path.join(get_root(), check_name, 'setup.py')

    if not specifier_set and force_pinned:
        message = f'Unspecified version found for dependency `{name}`: {format_check_usage(checks, source)}'
        echo_failure(message)
        annotate_error(file, message)
        failed = True
    elif len(specifier_set) > 1:
        message = (
            f'Multiple unstable version pins `{specifier_set}` found for dependency `{name}`: '
            f'{format_check_usage(checks, source)}'
        )
        echo_failure(message)
        annotate_error(file, message)
        failed = True
    elif specifier_set:
        specifier = get_next(specifier_set)

        if specifier.operator != '>=':
            message = (
                f'Forced version pin `{specifier}` found for dependency `{name}` '
                f'(use >= explicitly for base dependency): {format_check_usage(checks, source)}'
            )
            echo_failure(message)
            annotate_error(file, message)
            failed = True

        if min_base_version is not None and min_base_version not in specifier:
            message = (
                f'Minimum datadog_checks_base version `{min_base_version}` not satisfied by dependency specifier'
                f'`{specifier}`: {format_check_usage(checks, source)}'
            )
            echo_failure(message)
            annotate_error(file, message)
            failed = True

    return not failed


def verify_dependency(source, name, python_versions, file):
    for dependency_definitions in python_versions.values():
        # Identify dependencies that are defined multiple times for the same set of environment markers
        requirements = [Requirement(dep) for dep in dependency_definitions]
        markers = {req.marker for req in requirements}
        if len(markers) != len(requirements):
            message = f'Multiple dependency definitions found for dependency `{name}`:\n'
            for dependency_definition, checks in dependency_definitions.items():
                message += f'    {dependency_definition} from: {format_check_usage([checks])}\n'
            message = message.rstrip()
            echo_failure(message)
            annotate_error(file, message)
            return False

        for dependency_definition, checks in dependency_definitions.items():
            requirement = Requirement(dependency_definition)
            specifier_set = requirement.specifier

            if not specifier_set:
                message = f'Unpinned version found for dependency `{name}`: {format_check_usage(checks, source)}'
                echo_failure(message)
                annotate_error(file, message)
                return False
            elif len(specifier_set) > 1:
                message = (
                    f'Multiple unstable version pins `{specifier_set}` found for dependency `{name}` '
                    f'(use a single == explicitly): {format_check_usage(checks, source)}'
                )
                echo_failure(message)
                annotate_error(file, message)
                return False

            specifier = get_next(specifier_set)
            if specifier.operator != '==':
                message = (
                    f'Unstable version pin `{specifier}` found for dependency `{name}` '
                    f'(use == explicitly): {format_check_usage(checks, source)}'
                )
                echo_failure(message)
                annotate_error(file, message)
                return False

    return True


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Verify dependencies across all checks')
@click.argument('check', shell_complete=complete_valid_checks, required=False)
@click.option(
    '--require-base-check-version', is_flag=True, help='Require specific version for datadog-checks-base requirement'
)
@click.option(
    '--min-base-check-version', help='Specify minimum version for datadog-checks-base requirement, e.g. `11.0.0`'
)
def dep(check, require_base_check_version, min_base_check_version):
    """
    This command will:

    \b
    * Verify the uniqueness of dependency versions across all checks, or optionally a single check
    * Verify all the dependencies are pinned.
    * Verify the embedded Python environment defined in the base check and requirements
      listed in every integration are compatible.
    * Verify each check specifies a `CHECKS_BASE_REQ` variable for `datadog-checks-base` requirement
    * Optionally verify that the `datadog-checks-base` requirement is lower-bounded
    * Optionally verify that the `datadog-checks-base` requirement satisfies specific version
    """
    failed = False
    checks = process_checks_option(check, source='valid_checks', extend_changed=True)
    root = get_root()
    agent_dependencies, agent_errors = read_agent_dependencies()
    agent_dependencies_file = get_agent_requirements()
    annotate_errors(agent_dependencies_file, agent_errors)
    if agent_errors:
        for agent_error in agent_errors:
            echo_failure(agent_error)
        abort()

    for check_name in checks:
        if has_project_file(check_name):
            req_source = get_project_file(check_name)
            base_req_source = req_source
        else:
            req_source = os.path.join(root, check_name, 'requirements.in')
            base_req_source = os.path.join(root, check_name, 'setup.py')

        check_dependencies, check_errors = read_check_dependencies(check_name)
        annotate_errors(req_source, check_errors)
        if check_errors:
            for check_error in check_errors:
                echo_failure(check_error)
            abort()

        check_base_dependencies, check_base_errors = read_check_base_dependencies(check_name)
        annotate_errors(base_req_source, check_base_errors)
        if check_base_errors:
            for check_error in check_base_errors:
                echo_failure(check_error)
            abort()

        for name, versions in sorted(check_dependencies.items()):
            if not verify_dependency('Checks', name, versions, req_source):
                failed = True

            if name not in agent_dependencies:
                failed = True
                message = (
                    f'Dependency {name} found in the {check_name} integration requirements '
                    'but not in the agent requirements, run `ddev dep freeze` to sync them.'
                )
                echo_failure(message)
                annotate_error(req_source, message)

    check_base_dependencies, check_base_errors = read_check_base_dependencies(checks)
    check_dependencies, check_errors = read_check_dependencies(checks)

    for name, dependency in sorted(check_base_dependencies.items()):
        if not verify_base_dependency(
            'Base Checks', name, dependency, require_base_check_version, min_base_check_version
        ):
            failed = True

    for name, python_versions in sorted(agent_dependencies.items()):
        if not verify_dependency('Agent', name, python_versions, agent_dependencies_file):
            failed = True

        # Check that this dependency defined on the agent requirements is actually used
        # This only makes sense when we take all check dependencies into account
        if check is None and name not in check_dependencies:
            failed = True
            message = f'Stale dependency needs to be removed by syncing: {name}'
            echo_failure(message)
            annotate_error(agent_dependencies_file, message)
            continue

        # Look for version mismatches for this dependency against individual checks
        agent_dependency_definitions = get_dependency_set(python_versions)
        check_dependency_definitions = get_dependency_set(check_dependencies[name])

        # Only report mismatches when this dependency is actually present within the checks specified
        if check_dependency_definitions and not check_dependency_definitions.issubset(agent_dependency_definitions):
            failed = True
            message = (
                f'Mismatch for dependency `{name}`:\n'
                f'    Agent: {" | ".join(sorted(agent_dependency_definitions))}\n'
                f'    Checks: {" | ".join(sorted(check_dependency_definitions))}'
            )
            echo_failure(message)
            annotate_error(agent_dependencies_file, message)
            continue

        if failed:
            abort()
    echo_success("All dependencies are valid!")
