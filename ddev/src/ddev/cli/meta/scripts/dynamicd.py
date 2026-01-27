# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""CLI command for DynamicD - Smart fake data generator."""

from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command("dynamicd", short_help="Generate realistic fake telemetry data using AI")
@click.argument("integration")
@click.option(
    "--scenario",
    "-s",
    type=click.Choice(["healthy", "degraded", "incident", "recovery", "peak_load", "maintenance"]),
    default=None,
    help="Scenario to simulate. If not provided, shows interactive menu.",
)
@click.option(
    "--duration",
    "-d",
    type=int,
    default=0,
    help="Duration in seconds. Default: 0 (run forever until Ctrl+C)",
)
@click.option(
    "--rate",
    "-r",
    type=int,
    default=100,
    help="Target metrics per batch (batches sent every 10s). Default: 100",
)
@click.option(
    "--save",
    is_flag=True,
    help="Save the generated script to the integration's fake_data/ directory",
)
@click.option(
    "--show-only",
    is_flag=True,
    help="Only show the generated script, don't execute it",
)
@click.option(
    "--timeout",
    type=int,
    default=None,
    help="Execution timeout in seconds (for testing). Default: no timeout",
)
@click.option(
    "--all-metrics",
    is_flag=True,
    help="Generate ALL metrics from metadata.csv, not just dashboard metrics. Use for load testing.",
)
@click.option(
    "--sandbox/--no-sandbox",
    default=True,
    help="Run script in Docker container for isolation (default: enabled). Use --no-sandbox to run directly.",
)
@click.pass_obj
def dynamicd(
    app: Application,
    integration: str,
    scenario: str | None,
    duration: int,
    rate: int,
    save: bool,
    show_only: bool,
    timeout: int | None,
    all_metrics: bool,
    sandbox: bool,
) -> None:
    """Generate realistic fake telemetry data for an integration using AI.

    DynamicD uses Claude to analyze your integration's metrics and generate
    a sophisticated simulator that produces realistic, scenario-aware data.

    \b
    Examples:
        # Interactive scenario selection
        ddev meta scripts dynamicd ibm_mq

        # Specific scenario
        ddev meta scripts dynamicd ibm_mq --scenario incident

        # Save the script for later use
        ddev meta scripts dynamicd ibm_mq --scenario healthy --save

        # Just show the generated script
        ddev meta scripts dynamicd ibm_mq --show-only

    \b
    For detailed documentation, see:
    https://github.com/DataDog/integrations-core/blob/master/ddev/src/ddev/cli/meta/scripts/_dynamicd/README.md
    """
    # All imports are lazy to avoid impacting ddev startup time
    from ddev.cli.meta.scripts._dynamicd.cli import run_dynamicd

    run_dynamicd(
        app=app,
        integration=integration,
        scenario=scenario,
        duration=duration,
        rate=rate,
        save=save,
        show_only=show_only,
        timeout=timeout,
        all_metrics=all_metrics,
        sandbox=sandbox,
    )
