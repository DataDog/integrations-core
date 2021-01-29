# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ..console import CONTEXT_SETTINGS
from .agent_reqs import agent_reqs
from .agent_signature import legacy_signature
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
from .package import package
from .readmes import readmes
from .recommended_monitors import recommended_monitors
from .saved_views import saved_views
from .service_checks import service_checks

ALL_COMMANDS = (
    agent_reqs,
    ci,
    codeowners,
    config,
    dashboards,
    dep,
    eula,
    jmx_metrics,
    http,
    legacy_signature,
    imports,
    manifest,
    metadata,
    package,
    readmes,
    recommended_monitors,
    saved_views,
    service_checks,
)


@click.group(context_settings=CONTEXT_SETTINGS, short_help='Verify certain aspects of the repo')
def validate():
    pass


for command in ALL_COMMANDS:
    validate.add_command(command)
