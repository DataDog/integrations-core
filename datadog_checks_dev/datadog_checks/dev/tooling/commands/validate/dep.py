# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ....utils import get_next
from ...dependencies import read_agent_dependencies, read_check_dependencies
from ..console import CONTEXT_SETTINGS, abort, echo_failure


def get_marker_string(dependency_definition):
    marker = dependency_definition.requirement.marker
    if marker is None:
        return '<N/A>'

    return str(marker)


def format_check_usage(checks, default=None):
    if not checks:
        return default

    num_checks = len(checks)
    if num_checks == 1:
        return checks[0]
    elif num_checks == 2:
        return f'{checks[0]} and {checks[1]}'
    else:
        remaining = num_checks - 2
        plurality = 's' if remaining > 1 else ''
        return f'{checks[0]}, {checks[1]}, and {remaining} other{plurality}'


def verify_dependency(source, name, versions):
    markers = {}
    for specifier_set, dependency_definitions in versions.items():
        checks = set()

        for dependency_definition in dependency_definitions:
            check_name = dependency_definition.check_name
            if check_name is not None:
                checks.add(check_name)

            marker = get_marker_string(dependency_definition)
            if marker in markers:
                existing_check_name, existing_specifier_set = markers[marker]
                if existing_specifier_set != specifier_set:
                    echo_failure(f'Multiple version specifiers found for marker `{marker}` of dependency `{name}`:')
                    echo_failure(f'    {specifier_set} from: {check_name or source}')
                    echo_failure(f'    {existing_specifier_set} from: {existing_check_name or source}')
                    return False
            else:
                markers[marker] = (check_name, specifier_set)

        checks = sorted(checks)

        if not specifier_set:
            echo_failure(f'Unpinned version found for dependency `{name}`: {format_check_usage(checks, source)}')
            return False
        elif len(specifier_set) > 1:
            echo_failure(
                f'Multiple unstable version pins `{specifier_set}` found for dependency `{name}` '
                f'(use a single == explicitly): {format_check_usage(checks, source)}'
            )
            return False

        specifier = get_next(specifier_set)
        if specifier.operator != '==':
            echo_failure(
                f'Unstable version pin `{specifier}` found for dependency `{name}` '
                f'(use == explicitly): {format_check_usage(checks, source)}'
            )
            return False

    return True


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Verify dependencies across all checks')
def dep():
    """
    This command will:

    * Verify the uniqueness of dependency versions across all checks.
    * Verify all the dependencies are pinned.
    * Verify the embedded Python environment defined in the base check and requirements
      listed in every integration are compatible.
    """
    failed = False
    check_dependencies, check_errors = read_check_dependencies()

    if check_errors:
        for check_error in check_errors:
            echo_failure(check_error)

        abort()

    agent_dependencies, agent_errors = read_agent_dependencies()

    if agent_errors:
        for agent_error in agent_errors:
            echo_failure(agent_error)

        abort()

    for name, versions in sorted(check_dependencies.items()):
        if not verify_dependency('Checks', name, versions):
            failed = True

        if name not in agent_dependencies:
            failed = True
            echo_failure(f'Dependency needs to be synced: {name}')

    for name, versions in sorted(agent_dependencies.items()):
        if not verify_dependency('Agent', name, versions):
            failed = True

        if name not in check_dependencies:
            failed = True
            echo_failure(f'Stale dependency needs to be removed by syncing: {name}')
            continue

        agent_versions = sorted(versions, key=lambda v: str(v))
        check_versions = sorted(check_dependencies[name], key=lambda v: str(v))

        if agent_versions != check_versions:
            failed = True
            echo_failure(f'Version mismatch for dependency `{name}`:')
            echo_failure(f'    Agent: {" | ".join(map(str, agent_versions))}')
            echo_failure(f'    Checks: {" | ".join(map(str, check_versions))}')
            continue

        for specifier_set in agent_versions:
            agent_dependency_definitions = versions[specifier_set]
            check_dependency_definitions = check_dependencies[name][specifier_set]

            agent_markers = sorted(
                set(get_marker_string(dependency_definition) for dependency_definition in agent_dependency_definitions)
            )
            check_markers = sorted(
                set(get_marker_string(dependency_definition) for dependency_definition in check_dependency_definitions)
            )

            if agent_markers != check_markers:
                failed = True
                echo_failure(f'Marker mismatch for dependency `{name}`:')
                echo_failure(f'    Agent: {" | ".join(agent_markers)}')
                echo_failure(f'    Checks: {" | ".join(check_markers)}')

    if failed:
        abort()
