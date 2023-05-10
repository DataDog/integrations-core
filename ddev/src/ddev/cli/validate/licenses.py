# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application

@click.command(short_help='NEW Validate integration manifests')
@click.option('--sync', '-s', is_flag=True, help='Generate the `LICENSE-3rdparty.csv` file')
@click.pass_context
def licenses(ctx: click.Context, sync):
    app: Application = ctx.obj
    validation_tracker = app.create_validation_tracker('Licenses')

    # Validate that all values in the constants (EXPLICIT_LICENSES and PACKAGE_REPO_OVERRIDES) appear in LICENSE-3rdparty.csv

    # Call legacy licenses validation
    print("Invoking just the legacy validation")
    from datadog_checks.dev.tooling.commands.validate.licenses import licenses as legacy_licenses_validation

    ctx.invoke(legacy_licenses_validation, sync=sync)
    validation_tracker.display()