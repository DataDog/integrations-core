# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""CLI interface for DynamicD."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import click
import requests

from ddev.cli.meta.scripts.dynamicd.constants import (
    DEFAULT_DURATION_SECONDS,
    DEFAULT_METRICS_PER_BATCH,
    SCENARIOS,
)

if TYPE_CHECKING:
    from ddev.cli.application import Application


def validate_org(api_key: str, app_key: str | None, site: str) -> tuple[bool, str, bool]:
    """Validate API key and return (is_internal_org, org_name, key_valid).

    Checks if the API key belongs to a Datadog internal org (HQ or Staging).
    Note: Org lookup requires an Application Key. If not provided, we can only
    validate the API key works but cannot determine the org name.
    """
    # First validate the API key
    try:
        resp = requests.get(
            f"https://api.{site}/api/v1/validate",
            headers={"DD-API-KEY": api_key},
            timeout=10,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        return False, f"Unknown (API key validation failed: {e})", False

    # API key is valid. Now try to get org info (requires app key)
    if not app_key:
        return False, "(org lookup requires app_key - set orgs.<org>.app_key)", True

    try:
        org_resp = requests.get(
            f"https://api.{site}/api/v1/org",
            headers={"DD-API-KEY": api_key, "DD-APPLICATION-KEY": app_key},
            timeout=10,
        )
        org_resp.raise_for_status()
        org_data = org_resp.json()

        # The API can return either:
        # - {"org": {"name": "..."}} for single org
        # - {"orgs": [{"name": "..."}, ...]} for multi-org accounts
        org_info = None
        if "org" in org_data:
            org_info = org_data["org"]
        elif "orgs" in org_data and org_data["orgs"]:
            # For multi-org, use the first (parent) org
            org_info = org_data["orgs"][0]

        if org_info:
            org_name = org_info.get("name", "Unknown")
        else:
            org_name = "Unknown"

        is_internal = "datadog" in org_name.lower()
        return is_internal, org_name, True
    except requests.RequestException as e:
        # Org lookup failed but key is valid
        return False, f"(org lookup failed: {e})", True
    except Exception as e:
        return False, f"(unexpected error: {type(e).__name__}: {e})", True


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
    from ddev.cli.meta.scripts.dynamicd.executor import (
        execute_script,
        is_docker_available,
        save_script,
        validate_script_syntax,
    )
    from ddev.cli.meta.scripts.dynamicd.generator import GeneratorError, generate_simulator_script

    # Get the integration
    try:
        intg = app.repo.integrations.get(integration)
    except OSError:
        app.abort(f"Unknown integration: {integration}")

    # Check for metrics
    if not intg.has_metrics:
        app.abort(f"Integration '{integration}' has no metrics defined in metadata.csv")

    # Validate numeric options
    if duration < 0:
        app.abort("Duration cannot be negative")
    if rate <= 0:
        app.abort("Rate must be a positive number")

    # Handle sandbox mode (default: enabled)
    use_sandbox = sandbox
    if use_sandbox and not is_docker_available():
        app.display_error("Docker is not available. Install Docker or use --no-sandbox.")
        app.abort()

    # Get LLM API key from config or environment variable
    llm_api_key = app.config.raw_data.get("dynamicd", {}).get("llm_api_key")
    if not llm_api_key:
        llm_api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not llm_api_key:
        app.display_error(
            "LLM API key not configured. Either:\n"
            "  1. Set env var: export ANTHROPIC_API_KEY=<your-key>\n"
            "  2. Or run: ddev config set dynamicd.llm_api_key <your-key>"
        )
        app.abort()

    # Get Datadog API key from org config
    dd_api_key = app.config.org.config.get("api_key")
    if not dd_api_key:
        app.display_error(
            "Datadog API key not configured. Set it with:\n  ddev config set orgs.<org>.api_key <YOUR_DD_API_KEY>"
        )
        app.abort()

    # Get Datadog site and app key
    dd_site = app.config.org.config.get("site", "datadoghq.com")
    dd_app_key = app.config.org.config.get("app_key")

    # Validate org and warn if internal Datadog org
    app.display_info("Validating Datadog API key...")
    is_internal_org, org_name, key_valid = validate_org(dd_api_key, dd_app_key, dd_site)

    if not key_valid:
        app.display_error(f"API key validation failed: {org_name}")
        app.abort()

    app.display_info(f"  Target org: {org_name}")
    app.display_info(f"  Site: {dd_site}")
    app.display_info("")

    if is_internal_org:
        app.display_warning("=" * 60)
        app.display_warning("WARNING: You are about to send fake data to a Datadog internal org!")
        app.display_warning(f"  Org: {org_name}")
        app.display_warning(f"  Site: {dd_site}")
        app.display_warning("=" * 60)
        app.display_warning("")
        confirm = click.prompt(
            "Are you sure you want to continue? Type 'y' to proceed",
            default="n",
            show_default=False,
        )
        if confirm.lower() != "y":
            app.display_info("Aborted by user.")
            app.abort()

    # Interactive scenario selection if not provided
    if scenario is None:
        scenario = _select_scenario_interactive(app)
        if scenario is None:
            app.abort("No scenario selected")

    # Type narrowing: scenario is guaranteed to be str after the above check
    assert scenario is not None

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
    app.display_info(f"  Sandbox:     {'Docker' if use_sandbox else 'disabled'}")
    app.display_info("")

    # Build context
    app.display_info("Building integration context...")
    context = build_context(intg, all_metrics=all_metrics)
    if all_metrics:
        app.display_info(f"   Found {len(context.metrics)} metrics (ALL will be generated)")
    else:
        app.display_info(
            f"   Found {len(context.metrics)} metrics, {len(context.dashboard_metrics)} dashboard metrics (priority)"
        )

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
        sandbox=use_sandbox,
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
