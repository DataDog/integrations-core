# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click
from ddev.tooling.commands.validate.agent_reqs import agent_reqs
from ddev.tooling.commands.validate.agent_signature import legacy_signature
from ddev.tooling.commands.validate.all_validations import all
from ddev.tooling.commands.validate.codeowners import codeowners
from ddev.tooling.commands.validate.config import config
from ddev.tooling.commands.validate.dashboards import dashboards
from ddev.tooling.commands.validate.dep import dep
from ddev.tooling.commands.validate.eula import eula
from ddev.tooling.commands.validate.imports import imports
from ddev.tooling.commands.validate.integration_style import integration_style
from ddev.tooling.commands.validate.jmx_metrics import jmx_metrics
from ddev.tooling.commands.validate.license_headers import license_headers
from ddev.tooling.commands.validate.models import models
from ddev.tooling.commands.validate.package import package
from ddev.tooling.commands.validate.readmes import readmes
from ddev.tooling.commands.validate.saved_views import saved_views
from ddev.tooling.commands.validate.service_checks import service_checks
from ddev.tooling.commands.validate.typos import typos

from ddev.cli.validate.ci import ci
from ddev.cli.validate.http import http
from ddev.cli.validate.labeler import labeler
from ddev.cli.validate.licenses import licenses
from ddev.cli.validate.metadata import metadata
from ddev.cli.validate.openmetrics import openmetrics
from ddev.cli.validate.version import version


@click.group(short_help='Verify certain aspects of the repo')
def validate():
    """
    Verify certain aspects of the repo.
    """


validate.add_command(agent_reqs)
validate.add_command(all)
validate.add_command(ci)
validate.add_command(codeowners)
validate.add_command(config)
validate.add_command(dashboards)
validate.add_command(dep)
validate.add_command(eula)
validate.add_command(http)
validate.add_command(imports)
validate.add_command(integration_style)
validate.add_command(jmx_metrics)
validate.add_command(labeler)
validate.add_command(legacy_signature)
validate.add_command(license_headers)
validate.add_command(licenses)
validate.add_command(metadata)
validate.add_command(models)
validate.add_command(openmetrics)
validate.add_command(package)
validate.add_command(readmes)
validate.add_command(saved_views)
validate.add_command(service_checks)
validate.add_command(typos)
validate.add_command(version)
