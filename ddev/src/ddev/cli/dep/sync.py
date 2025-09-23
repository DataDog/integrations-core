# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ddev.cli.dep.common import (
    read_agent_dependencies,
    read_check_dependencies,
    update_check_dependencies,
    update_project_dependency,
)


def get_dependency_set(python_versions):
    return {
        dependency_definition
        for dependency_definitions in python_versions.values()
        for dependency_definition in dependency_definitions
    }


@click.command()
@click.pass_obj
def sync(app):
    """
    Synchronize integration dependency spec with that of the agent as a whole.

    Reads dependency spec from agent_requirements.in and propagates it to all integrations.
    For each integration we propagate only the relevant parts (i.e. its direct dependencies).
    """
    agent_dependencies, errors = read_agent_dependencies(app.repo)

    if errors:
        for error in errors:
            app.display_error(error)
        app.abort()

    check_dependencies, check_errors = read_check_dependencies(app.repo)

    if check_errors:
        for error in check_errors:
            app.display_error(error)
        app.abort()

    updated_checks = set()
    for name, python_versions in check_dependencies.items():
        check_dependency_definitions = get_dependency_set(python_versions)
        agent_dependency_definitions = get_dependency_set(agent_dependencies[name])

        if check_dependency_definitions != agent_dependency_definitions:
            for dependency_definition in agent_dependency_definitions:
                updated_checks.update(update_project_dependency(python_versions, dependency_definition))

    if not updated_checks:
        app.display_info('All dependencies synced.')
        return

    for check_name in sorted(updated_checks):
        update_check_dependencies(app.repo.integrations.get(check_name), check_dependencies)

    app.display_info(f'Files updated: {len(updated_checks)}')
