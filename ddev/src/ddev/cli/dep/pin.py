# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

import click
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from ddev.cli.dep.common import read_check_dependencies, update_check_dependencies, update_project_dependency


@click.command(short_help='Pin a dependency for all checks that require it')
@click.argument('definition')
@click.pass_obj
def pin(app, definition):
    """Pin a dependency for all checks that require it."""
    dependencies, errors = read_check_dependencies(app.repo)

    if errors:
        for error in errors:
            app.display_error(error)

        app.abort()

    requirement = Requirement(definition)
    package = canonicalize_name(requirement.name)
    if package not in dependencies:
        app.abort(f'Unknown package: {package}')

    new_dependencies = copy.deepcopy(dependencies)
    python_versions = new_dependencies[package]
    checks = update_project_dependency(python_versions, definition)
    if new_dependencies == dependencies:
        app.abort('No dependency definitions to update')

    for check_name in sorted(checks):
        update_check_dependencies(app.repo.integrations.get(check_name), new_dependencies)

    app.display_info(f'Files updated: {len(checks)}')
