# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click
from urllib.parse import urlparse

from datadog_checks.dev.tooling.commands.meta.prometheus import prom
from datadog_checks.dev.tooling.commands.console import CONTEXT_SETTINGS
from ddev.cli.meta.auto_build.orchestrator import AutoBuildOrchestrator

@prom.command(context_settings=CONTEXT_SETTINGS, short_help='Auto build an OpenMetrics integration')
@click.argument('integration',type=str, required=True)
@click.option('-e', '--endpoint', type=str, required=True, help='The endpoint URL of the integration')
def auto_build(integration: str, endpoint: str):
    """
    Auto build an OpenMetrics integration.

    Args:
        integration: The name of the integration.

    \b
    Example:
    `$ ddev meta auto-build openmetrics -e http://localhost:8080/metrics`
    """
    # Validate that the endpoint is a valid URL format
    parsed_endpoint = urlparse(endpoint)
    if parsed_endpoint.scheme not in ('http', 'https') or not parsed_endpoint.netloc:
            raise click.UsageError(f"Invalid endpoint URL: '{endpoint}'. Please provide a URL like 'http://host:port/path'.")

    orchestrator = AutoBuildOrchestrator(integration, endpoint)
    orchestrator.run()