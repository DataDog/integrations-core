# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""n8n lab traffic generator.

Brings up the standard n8n test environment via ``ddev env start --base``,
imports a richer set of workflows than the integration tests use, activates
them, and then drives a continuous, configurable traffic mix against the
running container so a real Datadog Agent can ship the resulting metrics.
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
WORKFLOWS_DIR = LAB_DIR / "workflows"
CONFIG_PATH = LAB_DIR / "config.yaml"

CONTAINER = "n8n-test"
MAIN_BASE_URL = "http://localhost:5678"

# Stable IDs that match the workflow JSON files. Kept here to drive the
# import/activate/restart loop without re-parsing the JSON.
LAB_WORKFLOW_IDS: list[str] = [
    "labFastSuccess",
    "labSlowSuccess",
    "labAlwaysFail",
    "labFlaky",
    "labLongChain",
]

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


def _docker_exec(*cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "exec", CONTAINER, *cmd],
        check=check,
        capture_output=True,
        text=True,
    )


def _docker_cp(src: Path, dest: str) -> None:
    subprocess.check_call(["docker", "cp", str(src), f"{CONTAINER}:{dest}"])


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


def _import_lab_workflows(console: Console) -> None:
    """Copy the lab workflow files into the running container, import & activate them."""
    console.print("[bold cyan]Copying lab workflows into the container...[/bold cyan]")
    _docker_exec("mkdir", "-p", "/lab/workflows")
    for path in sorted(WORKFLOWS_DIR.glob("*.json")):
        _docker_cp(path, f"/lab/workflows/{path.name}")

    console.print("[bold cyan]Importing & activating lab workflows...[/bold cyan]")
    for path in sorted(WORKFLOWS_DIR.glob("*.json")):
        result = _docker_exec("n8n", "import:workflow", f"--input=/lab/workflows/{path.name}", check=False)
        if result.returncode != 0:
            console.print(f"[bold red]Failed to import {path.name}:[/bold red]\n{result.stdout}\n{result.stderr}")
            sys.exit(1)
    for wf_id in LAB_WORKFLOW_IDS:
        _docker_exec("n8n", "update:workflow", f"--id={wf_id}", "--active=true")

    console.print("[bold cyan]Restarting n8n so webhooks register...[/bold cyan]")
    subprocess.check_call(
        ["docker", "compose", "-f", str(LAB_DIR.parent / "docker" / "docker-compose.yaml"), "restart", "n8n"]
    )
    _wait_for_endpoint(f"{MAIN_BASE_URL}/healthz")
    console.print("[bold green]Lab workflows are live.[/bold green]")


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

    console.print(f"[dim]Traffic config: {CONFIG_PATH}\nEdit it while the lab runs to change the mix.[/dim]\n")

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
    """Bring up the n8n test environment + agent and import lab workflows on top."""
    console = Console()
    console.print(f"[bold cyan]Starting environment {env} via ddev (this also starts the Agent)...[/bold cyan]")
    rc = subprocess.call(["ddev", "env", "start", "n8n", "--base", env, "-e", "DD_LOGS_ENABLED=true"])
    if rc != 0:
        console.print(f"[bold red]ddev env start failed (exit {rc})[/bold red]")
        sys.exit(rc)

    _wait_for_endpoint(f"{MAIN_BASE_URL}/healthz")
    _import_lab_workflows(console)
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
