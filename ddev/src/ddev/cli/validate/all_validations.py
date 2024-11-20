import click

from datadog_checks.dev.tooling.commands.validate.agent_reqs import agent_reqs
from datadog_checks.dev.tooling.commands.validate.agent_signature import legacy_signature
from datadog_checks.dev.tooling.commands.validate.all_validations import all
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
from datadog_checks.dev.tooling.commands.console import CONTEXT_SETTINGS, echo_info, echo_success
from datadog_checks.dev.tooling.utils import complete_valid_checks

from ddev.cli.validate.ci import ci
from ddev.cli.validate.http import http
from ddev.cli.validate.labeler import labeler
from ddev.cli.validate.licenses import licenses
from ddev.cli.validate.manifest import manifest
from ddev.cli.validate.metadata import metadata
from ddev.cli.validate.openmetrics import openmetrics
from ddev.cli.validate.version import version

# Validations, and repos they are limited to, if any
ALL_VALIDATIONS = (
    (agent_reqs, ('core',)),
    (ci, (None,)), #
    (codeowners, ('extras',)),
    (config, (None,)),
    (dashboards, (None,)),
    (dep, ('core',)),
    (eula, ('marketplace',)),
    (http, (None,)), #
    (imports, (None,)),
    (integration_style, (None,)), #
    (jmx_metrics, (None,)),
    (labeler, (None,)), #
    (legacy_signature, (None,)), #
    (license_headers, (None,)), #
    (licenses, (None,)), #
    (metadata, (None,)), #
    (models, (None,)),
    (openmetrics, (None,)), #
    (package, (None,)),
    (readmes, (None,)),
    (saved_views, (None,)),
    (service_checks, (None,)),
    (version, (None,)), #
)



# Ignore check argument for these validations
REPO_VALIDATIONS = {codeowners, dep, ci, labeler, licenses}
NEW_VALIDATIONS = {http, metadata,openmetrics, version}

FILE_INDENT = ' ' * 8

IGNORE_DEFAULT_INSTANCE = {'ceph', 'dotnetclr', 'gunicorn', 'marathon', 'pgbouncer', 'process', 'supervisord'}


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Run all CI validations for a repo')
@click.argument('check', shell_complete=complete_valid_checks, required=False)
@click.pass_context
def all2(ctx, check):
    """Run all CI validations for a repo.

    If `check` is specified, only the check will be validated, if check value is 'changed' will only apply to changed
    checks, an 'all' or empty `check` value will validate all README files.
    """
    repo_choice = ctx.obj['repo_choice']
    echo_info(f'Running validations for {repo_choice} repo ...')

    for validation, repos in ALL_VALIDATIONS:
        echo_success('---')
        if repos[0] is not None and repo_choice not in repos:
            echo_info(f'Skipping {validation.name}')
            continue
        echo_info(f'Executing validation {validation.name}')

        if validation in REPO_VALIDATIONS:
            result = ctx.invoke(validation)
        elif validation in NEW_VALIDATIONS:
            result = ctx.invoke(validation, integrations=(check,))
        else:
            result = ctx.invoke(validation, check=check)

        echo_success(result)