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

# Each entry: (command_func, applicable_repos, arg_mode, fix_param)
#   applicable_repos: tuple of repo names where this validator applies, or None for all repos
#   arg_mode:
#     'check'        — legacy validators that take a single `check` string argument
#     'integrations' — ddev validators that take an `integrations` tuple argument
#     'repo'         — repo-level validators that take no check/integration argument
#   fix_param: the keyword argument name for auto-fixing ('sync', 'fix'), or None if not supported
VALIDATORS: tuple[tuple[click.BaseCommand, tuple[str, ...] | None, str, str | None], ...] = (
    (agent_reqs, ('core',), 'check', None),
    (ci, None, 'repo', 'sync'),
    (codeowners, ('extras',), 'repo', None),
    (config, None, 'check', 'sync'),
    (dashboards, None, 'check', 'fix'),
    (dep, ('core',), 'repo', None),
    (eula, ('marketplace',), 'check', None),
    (http, None, 'integrations', None),
    (imports, None, 'check', None),
    (integration_style, None, 'check', None),
    (jmx_metrics, None, 'check', None),
    (labeler, ('core',), 'repo', 'sync'),
    (legacy_signature, None, 'check', None),
    (license_headers, None, 'check', 'fix'),
    (licenses, ('core',), 'repo', 'sync'),
    (metadata, None, 'integrations', 'sync'),
    (models, None, 'check', 'sync'),
    (openmetrics, None, 'integrations', None),
    (package, None, 'check', None),
    (readmes, None, 'check', None),
    (saved_views, None, 'check', None),
    (service_checks, None, 'check', 'sync'),
    (typos, None, 'check', 'fix'),
    (version, ('core',), 'integrations', None),
)


@click.command(short_help='Run all CI validations for a repo')
@click.argument('check', required=False)
@click.option(
    '--sync', '-s', is_flag=True, help='Auto-fix issues where supported (passes --sync or --fix to each validator)'
)
@click.pass_context
def all(ctx: click.Context, check: str | None, sync: bool) -> None:
    """Run all CI validations for a repo.

    If `check` is specified, only that check will be validated.
    A value of 'changed' will only validate changed checks.
    An empty or 'all' value will validate everything.
    """
    app: Application = ctx.obj
    repo_name = app.repo.name

    app.display_info(f'Running validations for {repo_name} repo ...')

    failed = []

    for func, repos, arg_mode, fix_param in VALIDATORS:
        app.display_info('---')

        if repos is not None and repo_name not in repos:
            app.display_info(f'Skipping {func.name}')
            continue

        app.display_info(f'Executing validation {func.name}')

        kwargs: dict[str, object] = {}
        if arg_mode == 'check':
            kwargs['check'] = check
        elif arg_mode == 'integrations':
            kwargs['integrations'] = (check,) if check else ()

        if sync and fix_param is not None:
            kwargs[fix_param] = True

        try:
            ctx.invoke(func, **kwargs)
        except SystemExit as e:
            if e.code:
                failed.append(func.name)
        except click.exceptions.Exit as e:
            if e.exit_code:
                failed.append(func.name)

    app.display_info('---')
    if failed:
        app.abort(f'Failed validations: {", ".join(failed)}')
