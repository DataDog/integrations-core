# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import glob
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


def _validate_openmetrics_integrations(contents, integration, package_file, validation_tracker):
    # Skip applying metric limit to custom OpenMetricsCheck
    if integration.display_name == "OpenMetrics":
        return

    # Note: can't include the closing parenthesis since some may include ConfigMixin
    if '(OpenMetricsBaseCheckV2' in contents or '(OpenMetricsBaseCheck' in contents:
        if 'DEFAULT_METRIC_LIMIT = 0' not in contents:
            validation_tracker.error(
                (integration.display_name, str(package_file)), message="`DEFAULT_METRIC_LIMIT = 0` is missing"
            )
        else:
            return True
    return False


@click.command(short_help='Validate OpenMetrics')
@click.argument('integrations', nargs=-1)
@click.pass_context
def openmetrics(ctx: click.Context, integrations: tuple[str, ...]):
    """Validate OpenMetrics metric limit.

    If `check` is specified, only the check will be validated, if check value is 'changed' will only apply to changed
    checks, an 'all' or empty `check` value will validate nothing.
    """

    app: Application = ctx.obj
    validation_tracker = app.create_validation_tracker('OpenMetrics Metric limit')

    app.display_waiting("Validating default metric limit for OpenMetrics integrations ...")
    if app.repo.name not in ('core', 'extras'):
        app.display_info(
            f"OpenMetrics validations is only enabled for core or "
            f"extras integrations, skipping for repo {app.repo.name}"
        )
        app.abort()

    for integration in app.repo.integrations.iter_packages(integrations):
        pass_validation = False
        python_files = glob.glob(str(integration.package_directory) + "**/*.py") + glob.glob(
            str(integration.package_directory) + "/**/*.py"
        )

        for file in python_files:
            try:
                f = open(file)
                contents = f.read()
            except Exception:
                app.display_info(f"Could not open or read file {file}, skipping")
            else:
                pass_validation = pass_validation or _validate_openmetrics_integrations(
                    contents, integration, file, validation_tracker
                )

        if pass_validation:
            validation_tracker.success()

    if validation_tracker.errors:
        validation_tracker.display()
        app.abort()

    validation_tracker.display()
