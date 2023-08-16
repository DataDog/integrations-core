# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command(short_help='Validate OpenMetrics')
@click.argument('integrations', nargs=-1)
@click.pass_obj
def openmetrics(app: Application, integrations: tuple[str, ...]):
    """Validate OpenMetrics metric limit.

    If `check` is specified, only the check will be validated, if check value is 'changed' will only apply to changed
    checks, an 'all' or empty `check` value will validate nothing.
    """
    validation_tracker = app.create_validation_tracker('OpenMetrics metric limit')

    app.display_waiting("Validating default metric limit for OpenMetrics integrations ...")
    if app.repo.name not in ('core', 'extras'):
        app.display_info(
            f"OpenMetrics validations is only enabled for core or "
            f"extras integrations, skipping for repo {app.repo.name}"
        )
        app.abort()

    excluded = set(app.repo.config.get('/overrides/validate/openmetrics/exclude', []))
    for integration in app.repo.integrations.iter_packages(integrations):
        if integration.name in excluded or not integration.is_integration:
            continue

        for f in integration.package_files():
            contents = f.read_text()

            # Note: can't include the closing parenthesis since some may include ConfigMixin
            if not ('(OpenMetricsBaseCheckV2' in contents or '(OpenMetricsBaseCheck' in contents):
                continue

            if 'DEFAULT_METRIC_LIMIT = 0' in contents:
                validation_tracker.success()
            else:
                validation_tracker.error(
                    (integration.display_name, str(f.relative_to(app.repo.path))),
                    message="`DEFAULT_METRIC_LIMIT = 0` is missing",
                )

    validation_tracker.display()

    if validation_tracker.errors:
        app.abort()
