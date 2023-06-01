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
@click.pass_context
def licenses(ctx: click.Context, sync):
    app: Application = ctx.obj
    validation_tracker = app.create_validation_tracker('Licenses')

    # Validate that all values in the constants (EXPLICIT_LICENSES and
    # PACKAGE_REPO_OVERRIDES) appear in agent_requirements.in file

    agent_requirements_path = app.repo.agent_requirements

    packages_set = set()
    with open(agent_requirements_path, 'r', encoding='utf-8') as f:
        for _i, line in enumerate(f.readlines()):
            requirement = Requirement(line.strip())
            packages_set.add(requirement.name)

    for name in app.repo.config.get('/overrides/explicit_licenses', {}):
        if name.lower() not in packages_set:
            validation_tracker.error(
                ("EXPLICIT_LICENSES", name),
                message=f"EXPLICIT_LICENSES contains additional package not in agent requirements: {name}",
            )

    for name in app.repo.config.get('/overrides/package_repo_overrides', {}):
        if name.lower() not in packages_set:
            validation_tracker.error(
                ("PACKAGE_REPO_OVERRIDES", name),
                message=f"PACKAGE_REPO_OVERRIDES contains additional package not in agent requirements: {name}",
            )

    if validation_tracker.errors:
        validation_tracker.display()
        app.abort()

    # Call legacy licenses validation
    print("Invoking the legacy validation")
    from datadog_checks.dev.tooling.commands.validate.licenses import licenses as legacy_licenses_validation

    ctx.invoke(legacy_licenses_validation, sync=sync)
    validation_tracker.display()
