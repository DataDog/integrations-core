# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""CLI interface for DynamicD."""

from __future__ import annotations

from typing import TYPE_CHECKING

import click

from ddev.cli.meta.scripts.dynamicd.constants import (
    DEFAULT_DURATION_SECONDS,
    DEFAULT_METRICS_PER_BATCH,
    SCENARIOS,
)

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command("dynamicd", short_help="Generate realistic fake telemetry data using AI")
@click.argument("integration")
@click.option(
    "--scenario",
    "-s",
    type=click.Choice(list(SCENARIOS.keys())),
    default=None,
    help="Scenario to simulate. If not provided, shows interactive menu.",
)
@click.option(
    "--duration",
    "-d",
    type=int,
    default=DEFAULT_DURATION_SECONDS,
    help="Duration in seconds. Default: 0 (run forever until Ctrl+C)",
)
@click.option(
    "--rate",
    "-r",
    type=int,
    default=DEFAULT_METRICS_PER_BATCH,
    help=f"Target metrics per batch (batches sent every 10s). Default: {DEFAULT_METRICS_PER_BATCH}",
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
):
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
    """
    from ddev.cli.meta.scripts.dynamicd.context_builder import build_context
    from ddev.cli.meta.scripts.dynamicd.executor import execute_script, save_script, validate_script_syntax
    from ddev.cli.meta.scripts.dynamicd.generator import GeneratorError, generate_simulator_script

    # Get the integration
    try:
        intg = app.repo.integrations.get(integration)
    except OSError:
        app.abort(f"Unknown integration: {integration}")

    # Check for metrics
    if not intg.has_metrics:
        app.abort(f"Integration '{integration}' has no metrics defined in metadata.csv")

    # Get LLM API key from config
    llm_api_key = app.config.raw_data.get("dynamicd", {}).get("llm_api_key")
    if not llm_api_key:
        app.display_error(
            "LLM API key not configured. Set it with:\n  ddev config set dynamicd.llm_api_key <YOUR_ANTHROPIC_API_KEY>"
        )
        app.abort()

    # Get Datadog API key from org config
    dd_api_key = app.config.org.config.get("api_key")
    if not dd_api_key:
        app.display_error(
            "Datadog API key not configured. Set it with:\n  ddev config set orgs.<org>.api_key <YOUR_DD_API_KEY>"
        )
        app.abort()

    # Get Datadog site
    dd_site = app.config.org.config.get("site", "datadoghq.com")

    # Interactive scenario selection if not provided
    if scenario is None:
        scenario = _select_scenario_interactive(app)
        if scenario is None:
            app.abort("No scenario selected")

    app.display_info("")
    app.display_info(f"╔{'═' * 60}╗")
    app.display_info(f"║{'DynamicD - Smart Fake Data Generator':^60}║")
    app.display_info(f"╚{'═' * 60}╝")
    app.display_info("")
    app.display_info(f"  Integration: {intg.display_name}")
    app.display_info(f"  Scenario:    {scenario}")
    if duration > 0:
        app.display_info(f"  Duration:    {duration}s")
    else:
        app.display_info("  Duration:    forever (Ctrl+C to stop)")
    app.display_info(f"  Rate:        {rate} metrics/batch (every 10s)")
    app.display_info(f"  Site:        {dd_site}")
    app.display_info("")

    # Build context
    app.display_info("Building integration context...")
    context = build_context(intg)
    app.display_info(f"   Found {len(context.metrics)} metrics, {len(context.config_options)} config options")

    # Status callback
    def on_status(msg: str) -> None:
        app.display_info(f"   {msg}")

    # Generate the script
    try:
        script = generate_simulator_script(
            context=context,
            scenario=scenario,
            dd_site=dd_site,
            metrics_per_batch=rate,
            duration=duration,
            api_key=llm_api_key,
            on_status=on_status,
        )
    except GeneratorError as e:
        app.abort(f"Failed to generate script: {e}")

    # Validate syntax
    is_valid, error = validate_script_syntax(script)
    if not is_valid:
        app.display_warning(f"Generated script has syntax errors: {error}")

    # Show only mode
    if show_only:
        app.display_info("")
        app.display_info("=" * 70)
        app.display_info("GENERATED SCRIPT")
        app.display_info("=" * 70)
        click.echo(script)
        app.display_info("=" * 70)
        return

    # Save if requested
    if save:
        saved_path = save_script(
            script=script,
            integration_path=intg.path,
            integration_name=intg.name,
            scenario=scenario,
        )
        app.display_success(f"Script saved to: {saved_path.relative_to(app.repo.path)}")

    # Execute the script
    app.display_info("")
    app.display_info("Starting simulation...")
    app.display_info("")

    result = execute_script(
        script=script,
        dd_api_key=dd_api_key,
        llm_api_key=llm_api_key,
        timeout=timeout,
        on_status=on_status,
    )

    # Output is streamed in real-time, so we don't need to print stdout again
    # Only show if there was stderr that wasn't streamed

    if result.stderr:
        app.display_warning("")
        app.display_warning("Errors:")
        click.echo(result.stderr, err=True)

    if result.success:
        app.display_success("")
        app.display_success(f"Simulation completed successfully (attempts: {result.attempts})")
    else:
        app.display_error("")
        app.display_error(f"Simulation failed after {result.attempts} attempts")
        app.abort()


def _select_scenario_interactive(app: Application) -> str | None:
    """Display interactive scenario selection menu."""
    app.display_info("")
    app.display_info("Select a scenario:")
    app.display_info("")

    scenarios_list = list(SCENARIOS.items())
    for i, (key, description) in enumerate(scenarios_list, 1):
        app.display_info(f"  {i}. {key:15} - {description}")

    app.display_info("")

    while True:
        try:
            choice = click.prompt(
                f"Enter number (1-{len(scenarios_list)})",
                type=int,
                default=1,
            )
            if 1 <= choice <= len(scenarios_list):
                return scenarios_list[choice - 1][0]
            app.display_warning(f"Please enter a number between 1 and {len(scenarios_list)}")
        except click.Abort:
            return None
        except ValueError:
            app.display_warning("Please enter a valid number")
