# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ..console import CONTEXT_SETTINGS
from .agent_reqs import agent_reqs
from .agent_signature import legacy_signature
from .all_validations import all
from .codeowners import codeowners
from .config import config
from .dashboards import dashboards
from .dep import dep
from .eula import eula
from .imports import imports
from .integration_style import integration_style
from .jmx_metrics import jmx_metrics
from .license_headers import license_headers
from .licenses import licenses
from .manifest import manifest
from .models import models
from .package import package
from .readmes import readmes
from .saved_views import saved_views
from .service_checks import service_checks
from .typos import typos

ALL_COMMANDS = (
    agent_reqs,
    all,
    codeowners,
    config,
    dashboards,
    dep,
    eula,
    imports,
    integration_style,
    jmx_metrics,
    legacy_signature,
    license_headers,
    licenses,
    manifest,
    models,
    package,
    readmes,
    saved_views,
    service_checks,
    typos,
)


@click.group(context_settings=CONTEXT_SETTINGS, short_help='Verify certain aspects of the repo')
def validate():
    pass


for command in ALL_COMMANDS:
    validate.add_command(command)
