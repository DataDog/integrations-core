# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import os
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


def _filter_openmetrics(contents, integration, package_file, validation_tracker):
    # Skip applying metric limit to custom OpenMetricsCheck
    if 'OpenMetricsCheck(OpenMetricsBaseCheck)' in contents:
        return

    # Note: can't include the closing parenthesis since some may include ConfigMixin
    if '(OpenMetricsBaseCheckV2' in contents or '(OpenMetricsBaseCheck' in contents:
        if 'DEFAULT_METRIC_LIMIT = 0' not in contents:
            validation_tracker.error(
                (integration.display_name, str(package_file)), message="`DEFAULT_METRIC_LIMIT = 0` is missing"
            )
        else:
            validation_tracker.success()


@click.command(short_help='Validate OpenMetrics')
@click.argument('integrations', nargs=-1)
@click.pass_context
def openmetrics(ctx: click.Context, integrations):
    """Validate OpenMetrics metric limit.

    If `check` is specified, only the check will be validated, if check value is 'changed' will only apply to changed
    checks, an 'all' or empty `check` value will validate nothing.
    """

    app: Application = ctx.obj
    validation_tracker = app.create_validation_tracker('OpenMetrics Metric limit')

    is_core = app.repo.name == 'core'
    is_extras = app.repo.name == 'extras'

    if not integrations:
        integrations = "all"

    app.display_info("Validating DEFAULT_METRIC_LIMIT = 0 for OpenMetrics integrations ...")
    if app.repo.name not in ('core', 'extras'):
        app.display_info(
            f"OpenMetrics validations is only enabled for core or "
            f"extras integrations, skipping for repo {app.repo.name}"
        )
        app.abort()

    for integration in app.repo.integrations.iter_packages(integrations):
        package_files = os.listdir(integration.package_directory)
        for package_file in package_files:
            check_file = integration.package_directory / package_file
            if os.path.isfile(check_file) and check_file.name.endswith(".py"):
                try:
                    f = open(check_file)
                    contents = f.read()
                except Exception:
                    app.display_info(f"Could not open or read file {check_file}, skipping")
                else:
                    _filter_openmetrics(contents, integration, package_file, validation_tracker)

    if validation_tracker.errors:
        validation_tracker.display()
        app.abort()

    validation_tracker.display()
