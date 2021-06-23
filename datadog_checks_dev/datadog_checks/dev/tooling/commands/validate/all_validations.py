# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ...utils import complete_valid_checks
from ..console import CONTEXT_SETTINGS, echo_info, echo_success
from .agent_reqs import agent_reqs
from .ci import ci
from .codeowners import codeowners
from .config import config
from .dashboards import dashboards
from .dep import dep
from .eula import eula
from .http import http
from .imports import imports
from .jmx_metrics import jmx_metrics
from .manifest import manifest
from .metadata import metadata
from .models import models
from .package import package
from .readmes import readmes
from .recommended_monitors import recommended_monitors
from .saved_views import saved_views
from .service_checks import service_checks

# Validations, and repos they are limited to, if any
ALL_VALIDATIONS = (
    (agent_reqs, ('core',)),
    (ci, ('core', 'extras', 'internal')),
    (codeowners, ('extras',)),
    (config, (None,)),
    (dashboards, (None,)),
    (dep, ('core',)),
    (eula, ('marketplace',)),
    (jmx_metrics, (None,)),
    (http, ('core',)),
    (imports, (None,)),
    (manifest, (None,)),
    (metadata, (None,)),
    (models, (None,)),
    (package, (None,)),
    (readmes, (None,)),
    (recommended_monitors, (None,)),
    (saved_views, (None,)),
    (service_checks, (None,)),
)

# Ignore check argument for these validations
REPO_VALIDATIONS = {ci, codeowners, dep}

FILE_INDENT = ' ' * 8

IGNORE_DEFAULT_INSTANCE = {'ceph', 'dotnetclr', 'gunicorn', 'marathon', 'pgbouncer', 'process', 'supervisord'}


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Run all CI validations for a repo')
@click.argument('check', autocompletion=complete_valid_checks, required=False)
@click.pass_context
def all(ctx, check):
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
        else:
            result = ctx.invoke(validation, check=check)

        echo_success(result)
