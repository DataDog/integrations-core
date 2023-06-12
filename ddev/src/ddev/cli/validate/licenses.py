# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click
from packaging.requirements import Requirement

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command(short_help='Validate third-party license list')
@click.option('--sync', '-s', is_flag=True, help='Generate the `LICENSE-3rdparty.csv` file')
@click.pass_obj
def licenses(app: Application, sync: bool):
    validation_tracker = app.create_validation_tracker('Licenses')

    # Validate that all values in the constants (EXPLICIT_LICENSES and
    # PACKAGE_REPO_OVERRIDES) appear in agent_requirements.in file

    agent_requirements_path = app.repo.agent_requirements

    packages_set = set()
    with open(agent_requirements_path, 'r', encoding='utf-8') as f:
        for _i, line in enumerate(f.readlines()):
            requirement = Requirement(line.strip())
            packages_set.add(requirement.name)

    for dependency_override, constant_name in [('licenses', 'EXPLICIT_LICENSES'), ('repo', 'PACKAGE_REPO_OVERRIDES')]:
        for name in app.repo.config.get(f'/overrides/dependencies/{dependency_override}', {}):
            if name.lower() not in packages_set:
                validation_tracker.error(
                    (constant_name, name),
                    message=f"{constant_name} contains additional package not in agent requirements: {name}",
                )

    if validation_tracker.errors:
        validation_tracker.display()
        app.abort()

    # Call legacy licenses validation
    from datadog_checks.dev.tooling.commands.validate.licenses import licenses as legacy_licenses_validation

    ctx.invoke(legacy_licenses_validation, sync=sync)
    validation_tracker.display()
