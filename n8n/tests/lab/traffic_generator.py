# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""n8n lab traffic generator.

The lab brings up a dedicated docker-compose (``tests/lab/docker-compose.yaml``)
that bind-mounts both the test fixtures and the lab workflow JSONs under
``/workflows/``. ``tests/conftest.py`` (gated on ``N8N_IS_LAB``) imports and
activates every workflow it finds there as part of ``ddev env start --base``,
so by the time this generator runs the webhooks are already live.

Ports are hardcoded in the lab compose, so the generator can assume
``localhost:5678`` and skip the dynamic discovery the integration tests need.
"""

from __future__ import annotations

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
LAB_DIR = Path(__file__).resolve().parent
CONFIG_PATH = LAB_DIR / "config.yaml"

MAIN_BASE_URL = "http://localhost:5678"

shutdown_event = asyncio.Event()
current_config: ConfigDict = {}


def _load_config(path: Path) -> tuple[ConfigDict, str]:
    try:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        return current_config, f"Config file {path} not found; using current values."
    except yaml.YAMLError as exc:
        return current_config, f"Failed to parse {path}: {exc}; using current values."

    if not isinstance(data, dict):
        return current_config, f"{path} must be a mapping at the top level; using current values."

    return data, ""


def _wait_for_endpoint(url: str, *, timeout: int = 90) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if httpx.get(url, timeout=2).status_code == 200:
                return
        except httpx.RequestError:
            pass
        time.sleep(2)
    raise RuntimeError(f"Endpoint {url} never became reachable")


def _signal_handler(_sig, _frame) -> None:
    shutdown_event.set()


def _print_row(console: Console, ts: str, scenario: str, target: str, status: str, latency_ms: str) -> None:
    table = Table(show_header=False, box=None, show_edge=False)
    table.add_column("Timestamp", style="dim", width=20)
    table.add_column("Scenario", width=10)
    table.add_column("Endpoint", width=28)
    table.add_column("Status", justify="right", width=14)
    table.add_column("Latency (ms)", justify="right", width=14)
    table.add_row(ts, scenario, target, status, latency_ms)
    console.print(table)


async def _hit(client: httpx.AsyncClient, console: Console, scenario: str, path: str) -> None:
    url = f"{MAIN_BASE_URL}{path}"
    ts = time.strftime("%H:%M:%S")
    start = time.perf_counter()
    try:
        resp = await client.get(url, timeout=10.0)
        latency_ms = f"{(time.perf_counter() - start) * 1000:.0f}"
        style = "green" if 200 <= resp.status_code < 400 else "red"
        _print_row(console, ts, scenario, path, f"[{style}]{resp.status_code}[/]", latency_ms)
    except httpx.TimeoutException:
        _print_row(console, ts, scenario, path, "[bold yellow]TIMEOUT[/]", "")
    except httpx.RequestError as exc:
        _print_row(console, ts, scenario, path, f"[bold red]ERR[/] {type(exc).__name__}", "")


def _draws(probability: float) -> int:
    """Return the number of times an event should fire this tick.

    ``probability`` is interpreted as expected count: ``2.5`` => 2 firings + a
    50% chance of a third. Values <= 1 act like a single Bernoulli trial.
    """
    whole = int(probability)
    fractional = probability - whole
    extra = 1 if random.random() < fractional else 0
    return whole + extra


async def _config_reloader(path: Path, console: Console) -> None:
    global current_config
    while not shutdown_event.is_set():
        new_config, error = _load_config(path)
        if error:
            console.print(f"[bold yellow]{error}[/bold yellow]")
        elif new_config != current_config:
            current_config = new_config
            console.print(f"[bold cyan]Reloaded config from {path}[/bold cyan]")
        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=float(current_config.get("reload_interval", 5)))
        except asyncio.TimeoutError:
            pass


async def _run_traffic(console: Console) -> None:
    global current_config
    current_config, error = _load_config(CONFIG_PATH)
    if error:
        console.print(f"[bold red]{error}[/bold red]")
        sys.exit(1)

    console.print(
        f"[dim]Traffic config: {CONFIG_PATH}\n"
        f"n8n base URL: {MAIN_BASE_URL}\n"
        "Edit config.yaml while the lab runs to change the mix.[/dim]\n"
    )

    reloader = asyncio.create_task(_config_reloader(CONFIG_PATH, console))
    async with httpx.AsyncClient() as client:
        try:
            while not shutdown_event.is_set():
                tasks = []
                for path, probability in (current_config.get("webhook_probabilities") or {}).items():
                    for _ in range(_draws(float(probability))):
                        tasks.append(_hit(client, console, "webhook", path))
                for path, probability in (current_config.get("api_probabilities") or {}).items():
                    for _ in range(_draws(float(probability))):
                        tasks.append(_hit(client, console, "api", path))
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                try:
                    await asyncio.wait_for(
                        shutdown_event.wait(),
                        timeout=float(current_config.get("tick_seconds", 1.0)),
                    )
                except asyncio.TimeoutError:
                    pass
        finally:
            reloader.cancel()
            try:
                await reloader
            except asyncio.CancelledError:
                pass


@click.group()
def cli() -> None:
    """n8n traffic lab commands."""


@cli.command()
@click.option("-e", "--env", default="py3.13-2", help="ddev env name to start (matches hatch matrix entry).")
def start(env: str) -> None:
    """Bring up the n8n lab compose + Datadog Agent.

    The lab compose bind-mounts the lab + test workflow JSONs under ``/workflows/``,
    and ``tests/conftest.py`` (in lab mode, gated on ``N8N_IS_LAB``) imports and
    activates them as part of ``ddev env start``. This command therefore does
    nothing fancy — it just hands off to ddev.
    """
    console = Console()
    console.print(f"[bold cyan]Starting environment {env} via ddev (this also starts the Agent)...[/bold cyan]")
    rc = subprocess.call(
        [
            "ddev",
            "env",
            "start",
            "n8n",
            "--base",
            env,
            "-e",
            "DD_LOGS_ENABLED=true",
            # Attach stdout tailers via Docker autodiscovery. Event-bus file logs are
            # configured in ``tests/conftest.py`` through the lab-only ``logs`` block.
            "-e",
            "DD_LOGS_CONFIG_CONTAINER_COLLECT_ALL=true",
        ]
    )
    if rc != 0:
        console.print(f"[bold red]ddev env start failed (exit {rc})[/bold red]")
        sys.exit(rc)

    _wait_for_endpoint(f"{MAIN_BASE_URL}/healthz")
    console.print(
        "\n[bold green]Lab is up.[/bold green] "
        "Run [bold]hatch run lab:generate[/bold] to start traffic, "
        "[bold]hatch run lab:stop[/bold] to tear down."
    )


@cli.command()
def generate() -> None:
    """Drive a continuous, configurable traffic mix against the running lab."""
    console = Console()
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    try:
        asyncio.run(_run_traffic(console))
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Traffic stopped.[/bold yellow]")


@cli.command()
@click.option("-e", "--env", default="py3.13-2", help="ddev env name to stop.")
def stop(env: str) -> None:
    """Tear down the lab environment."""
    console = Console()
    console.print(f"[bold cyan]Stopping environment {env}...[/bold cyan]")
    rc = subprocess.call(["ddev", "env", "stop", "n8n", env])
    if rc != 0:
        console.print(f"[bold red]ddev env stop failed (exit {rc})[/bold red]")
        sys.exit(rc)
    console.print("[bold green]Lab stopped.[/bold green]")


if __name__ == "__main__":
    cli()
