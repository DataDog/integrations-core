# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import asyncio
import random
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import click
import httpx
import yaml
from rich.console import Console
from rich.table import Table

ConfigDict = dict[str, Any]

shutdown_event = asyncio.Event()

# Global configuration that can be updated dynamically
current_config: ConfigDict = {}


def validate_config(config: ConfigDict) -> tuple[bool, str]:
    """
    Validate the configuration to ensure probabilities sum to 1.

    Returns:
        tuple: (is_valid, error_message)
    """
    if not config.get("request_probabilities"):
        return False, "Missing 'request_probabilities' section"

    probabilities = config["request_probabilities"]
    if not isinstance(probabilities, dict):
        return False, "'request_probabilities' must be a dictionary"

    if not probabilities:
        return False, "'request_probabilities' cannot be empty"

    # Check if all values are numeric and between 0 and 1
    for endpoint, prob in probabilities.items():
        if not isinstance(prob, (int, float)):
            return False, f"Probability for '{endpoint}' must be a number, got {type(prob).__name__}"

        if not (0 <= prob <= 1):
            return False, f"Probability for '{endpoint}' must be between 0 and 1, got {prob}"

    # Check if probabilities sum to approximately 1 (allow for floating point precision)
    total = sum(probabilities.values())
    if not (0.99 <= total <= 1.01):  # Allow 1% tolerance for floating point precision
        return False, f"Probabilities must sum to 1.0, current sum is {total:.3f}"

    return True, ""


def load_config(config_path: Path) -> tuple[ConfigDict, str]:
    """
    Load and validate configuration from YAML file.

    Returns:
        tuple: (config_dict, error_message). If error_message is not empty,
               config_dict will be the current_config (unchanged).
    """
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)

        # Validate the loaded configuration
        is_valid, error_message = validate_config(config)
        if not is_valid:
            return current_config, f"Invalid config in {config_path}: {error_message}. Keeping current configuration."

        return config, ""

    except FileNotFoundError:
        return current_config, f"Config file {config_path} not found. Using current values."
    except yaml.YAMLError as e:
        return current_config, f"Error parsing config file {config_path}: {e}. Using current values."
    except Exception as e:
        return current_config, f"Unexpected error loading config file {config_path}: {e}. Using current values."


async def config_reloader(config_path: Path, console: Console):
    """Async task to periodically reload configuration from YAML file."""
    global current_config

    while not shutdown_event.is_set():
        try:
            new_config, error_message = load_config(config_path)

            if error_message:
                # Only print warning if it's a validation error (not file not found on first load)
                if "Invalid config" in error_message:
                    console.print(f"[bold red]Warning: {error_message}[/bold red]")
            elif new_config != current_config:
                current_config = new_config
                print_current_probabilities(console, "Configuration Updated - New Request Probabilities")

        except Exception as e:
            console.print(f"[bold red]Warning: Error during config reload: {e}[/bold red]")

        try:
            reload_interval = float(current_config.get("reload_interval", 5))
            await asyncio.wait_for(shutdown_event.wait(), timeout=reload_interval)
        except asyncio.TimeoutError:
            pass


def _print_row(console: Console, timestamp: str, endpoint: str, status: str, response_time: str):
    table = Table(show_header=False, box=None, show_edge=False)
    table.add_column("Timestamp", style="dim", width=20)
    table.add_column("Endpoint", width=30)
    table.add_column("Status", justify="right", width=25)
    table.add_column("Response Time (s)", justify="right", width=20)
    table.add_row(timestamp, endpoint, status, response_time)
    console.print(table)


async def _generate_traffic_for_endpoint(client: httpx.AsyncClient, console: Console, endpoint: str):
    url = f"http://localhost:8080{endpoint}"
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        start_time = time.time()
        response = await client.get(url, timeout=5.0)
        end_time = time.time()
        response_time = f"{(end_time - start_time):.2f}"
        status_code = response.status_code
        status_style = "green" if 200 <= status_code < 300 else "red"
        status = f"[{status_style}]{status_code}[/]"
        _print_row(console, timestamp, endpoint, status, response_time)
    except httpx.TimeoutException:
        _print_row(console, timestamp, endpoint, "[bold yellow]TIMEOUT[/]", "")
    except httpx.RequestError:
        _print_row(console, timestamp, endpoint, "[bold red]ERROR[/]", "")


async def _generate_cancelled_requests(client: httpx.AsyncClient, console: Console, endpoint: str):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        await client.get(f"http://localhost:8080{endpoint}", timeout=0.1)
    except httpx.TimeoutException:
        _print_row(console, timestamp, endpoint, "[bold yellow]CANCELLED (Timeout)[/]", "")
    except httpx.RequestError:
        _print_row(console, timestamp, endpoint, "[bold red]ERROR[/]", "")


def _signal_handler(sig, frame):
    shutdown_event.set()


async def _generate_traffic(console: Console):
    # Get the config file path (look for config.yaml in the same directory as this script)
    config_path = Path(__file__).parent / "config.yaml"

    # Load initial configuration
    global current_config
    current_config = load_config(config_path)[0]  # Extract the config dict from the tuple

    console.print("\n[bold cyan]Starting traffic generation...[/bold cyan]")
    console.print(f"[dim]Config file: {config_path}[/dim]")
    console.print("[dim]You can modify the config file to change request probabilities while running[/dim]\n")

    # Display initial probabilities
    print_current_probabilities(console, "Initial Request Probabilities")
    console.print()  # Add some spacing

    header = Table(show_header=True, header_style="bold magenta", box=None, show_edge=False)
    header.add_column("Timestamp", style="dim", width=20)
    header.add_column("Endpoint", width=30)
    header.add_column("Status", justify="right", width=25)
    header.add_column("Response Time (s)", justify="right", width=20)
    console.print(header)

    # Start the config reloader task
    config_task = asyncio.create_task(config_reloader(config_path, console))

    async with httpx.AsyncClient() as client:
        try:
            while not shutdown_event.is_set():
                tasks = []

                # Use current configuration for request probabilities
                request_probabilities = current_config.get("request_probabilities", {})

                for endpoint, probability in request_probabilities.items():
                    if random.random() < probability:
                        if endpoint == "/api/cancelled":
                            tasks.append(_generate_cancelled_requests(client, console, endpoint))
                        else:
                            tasks.append(_generate_traffic_for_endpoint(client, console, endpoint))

                if tasks:
                    await asyncio.gather(*tasks)

                try:
                    await asyncio.wait_for(shutdown_event.wait(), timeout=1)
                except asyncio.TimeoutError:
                    pass
        finally:
            # Cancel the config reloader task when shutting down
            config_task.cancel()
            try:
                await config_task
            except asyncio.CancelledError:
                pass


def print_current_probabilities(console: Console, title: str = "Current Request Probabilities"):
    """Print the current request probabilities in a formatted table."""
    if not current_config.get("request_probabilities"):
        return

    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("Endpoint", style="white", width=25)
    table.add_column("Probability", justify="right", style="green", width=15)
    table.add_column("Description", style="dim", width=25)

    endpoint_descriptions = {
        "/api/valid": "Successful requests",
        "/api/invalid": "Invalid requests",
        "/api/timeout": "Timeout scenarios",
        "/api/no-content-length": "Edge case scenarios",
        "/api/not-found": "404 errors",
        "/api/cancelled": "Cancelled requests",
    }

    probabilities = current_config.get("request_probabilities", {})
    for endpoint, probability in probabilities.items():
        description = endpoint_descriptions.get(endpoint, "Custom endpoint")
        table.add_row(endpoint, f"{probability:.2f}", description)

    console.print(table)


@click.group()
def cli():
    """Krakend traffic generator commands."""
    pass


@cli.command(context_settings={"ignore_unknown_options": True})
@click.option("-e", "--env", default="py3.12-2.10", help="The environment to use for the test environment.")
@click.pass_context
def start(ctx, env: str):
    """Start the Krakend test environment."""
    console = Console()

    console.print("[bold cyan]Starting the test environment...[/bold cyan]")
    command = [
        "ddev",
        "env",
        "start",
        "krakend",
        "--base",
        env,
        "-e",
        "DD_LOGS_ENABLED=true",
        # "-a",
        # "datadog/agent:latest",
    ]
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True
    )

    if process.stdout:
        for line in iter(process.stdout.readline, ""):
            console.print(line.strip())
        process.stdout.close()

    return_code = process.wait()

    if return_code != 0:
        console.print(f"[bold red]Error starting environment (exit code: {return_code})[/bold red]")
        sys.exit(1)
    else:
        console.print("[bold green]Environment started successfully.[/bold green]")

    console.print("\n[bold cyan]Performing health check...[/bold cyan]")
    try:
        response = httpx.get("http://localhost:8080/__health", timeout=5)
        if response.status_code == 200 and response.json().get("status") == "ok":
            console.print("[bold green]Health check passed. Krakend is running.[/bold green]")
        else:
            console.print(
                f"[bold red]Health check failed. Status code: {response.status_code}, Body: {response.text}[/bold red]"
            )
            sys.exit(1)
    except httpx.RequestError as e:
        console.print(f"[bold red]Health check failed: {e}[/bold red]")
        sys.exit(1)


@cli.command(context_settings={"ignore_unknown_options": True})
@click.pass_context
def generate(ctx):
    """Generate traffic to the running Krakend instance."""
    console = Console()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    try:
        asyncio.run(_generate_traffic(console))
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Traffic generation stopped.[/bold yellow]")


@cli.command(context_settings={"ignore_unknown_options": True})
@click.option("-e", "--env", default="py3.12-2.10", help="The environment to use for the test environment.")
@click.pass_context
def stop(ctx, env: str):
    """Stop the Krakend test environment."""
    console = Console()
    console.print("\n[bold cyan]Tearing down the test environment...[/bold cyan]")

    try:
        result = subprocess.run(["ddev", "env", "stop", "krakend", env], capture_output=True, text=True, timeout=60)

        if result.stdout.strip():
            console.print(result.stdout.strip())
        if result.stderr.strip():
            console.print(result.stderr.strip())

        if result.returncode == 0:
            console.print("[bold green]Environment stopped successfully.[/bold green]")
        else:
            console.print(f"[bold red]Error stopping environment (exit code: {result.returncode})[/bold red]")
            sys.exit(1)

    except Exception as e:
        console.print(f"[bold red]Error during cleanup: {e}[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    cli()
