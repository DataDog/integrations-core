# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click
from datadog_checks.dev.tooling.commands.validate.agent_reqs import agent_reqs
from datadog_checks.dev.tooling.commands.validate.agent_signature import legacy_signature
from datadog_checks.dev.tooling.commands.validate.codeowners import codeowners
from datadog_checks.dev.tooling.commands.validate.config import config
from datadog_checks.dev.tooling.commands.validate.dashboards import dashboards
from datadog_checks.dev.tooling.commands.validate.dep import dep
from datadog_checks.dev.tooling.commands.validate.eula import eula
from datadog_checks.dev.tooling.commands.validate.imports import imports
from datadog_checks.dev.tooling.commands.validate.integration_style import integration_style
from datadog_checks.dev.tooling.commands.validate.jmx_metrics import jmx_metrics
from datadog_checks.dev.tooling.commands.validate.license_headers import license_headers
from datadog_checks.dev.tooling.commands.validate.models import models
from datadog_checks.dev.tooling.commands.validate.package import package
from datadog_checks.dev.tooling.commands.validate.readmes import readmes
from datadog_checks.dev.tooling.commands.validate.saved_views import saved_views
from datadog_checks.dev.tooling.commands.validate.service_checks import service_checks
from datadog_checks.dev.tooling.commands.validate.typos import typos

from ddev.cli.validate.ci import ci
from ddev.cli.validate.http import http
from ddev.cli.validate.labeler import labeler
from ddev.cli.validate.licenses import licenses
from ddev.cli.validate.metadata import metadata
from ddev.cli.validate.openmetrics import openmetrics
from ddev.cli.validate.version import version

if TYPE_CHECKING:
    from ddev.cli.application import Application

# Each entry: (command_func, applicable_repos, arg_mode)
#   applicable_repos: tuple of repo names where this validator applies, or None for all repos
#   arg_mode:
#     'check'        — legacy validators that take a single `check` string argument
#     'integrations' — ddev validators that take an `integrations` tuple argument
#     'repo'         — repo-level validators that take no check/integration argument
VALIDATORS: tuple[tuple[click.BaseCommand, tuple[str, ...] | None, str], ...] = (
    (agent_reqs, ('core',), 'check'),
    (ci, None, 'repo'),
    (codeowners, ('extras',), 'repo'),
    (config, None, 'check'),
    (dashboards, None, 'check'),
    (dep, ('core',), 'repo'),
    (eula, ('marketplace',), 'check'),
    (http, None, 'integrations'),
    (imports, None, 'check'),
    (integration_style, None, 'check'),
    (jmx_metrics, None, 'check'),
    (labeler, ('core',), 'repo'),
    (legacy_signature, None, 'check'),
    (license_headers, None, 'check'),
    (licenses, ('core',), 'repo'),
    (metadata, None, 'integrations'),
    (models, None, 'check'),
    (openmetrics, None, 'integrations'),
    (package, None, 'check'),
    (readmes, None, 'check'),
    (saved_views, None, 'check'),
    (service_checks, None, 'check'),
    (typos, None, 'check'),
    (version, ('core',), 'integrations'),
)


@click.command(short_help='Run all CI validations for a repo')
@click.argument('check', required=False)
@click.pass_context
def all(ctx: click.Context, check: str | None) -> None:
    """Run all CI validations for a repo.

    If `check` is specified, only that check will be validated.
    A value of 'changed' will only validate changed checks.
    An empty or 'all' value will validate everything.
    """
    app: Application = ctx.obj
    repo_name = app.repo.name

    app.display_info(f'Running validations for {repo_name} repo ...')

    failed = []

    for func, repos, arg_mode in VALIDATORS:
        app.display_info('---')

        if repos is not None and repo_name not in repos:
            app.display_info(f'Skipping {func.name}')
            continue

        app.display_info(f'Executing validation {func.name}')

        try:
            if arg_mode == 'repo':
                ctx.invoke(func)
            elif arg_mode == 'integrations':
                ctx.invoke(func, integrations=(check,) if check else ())
            else:
                ctx.invoke(func, check=check)
        except SystemExit as e:
            if e.code:
                failed.append(func.name)
        except click.exceptions.Exit as e:
            if e.exit_code:
                failed.append(func.name)

    app.display_info('---')
    if failed:
        app.abort(f'Failed validations: {", ".join(failed)}')
