# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command('logs', short_help='Scaffold a logs-only integration')
@click.argument('name')
@click.option('--display-name', default=None, help='Human-readable display name for the integration.')
@click.option('--metrics-prefix', default=None, help='Metric namespace (e.g. `myintegration.`).')
@click.option('--platforms', default=None, help='Comma-separated list of `linux,windows,mac_os`.')
@click.option('--location', '-l', default=None, help='The directory where files will be written.')
@click.option('--quiet', '-q', is_flag=True, help='Show less output.')
@click.option('--dry-run', '-n', is_flag=True, help='Only show what would be created.')
@click.option('--include-manifest', is_flag=True, help='Generate a `manifest.json` (legacy behaviour).')
@click.option(
    '--skip-manifest',
    is_flag=True,
    help='[DEPRECATED] No-op; manifest-less is now the default. Use `--include-manifest` to opt back in.',
)
@click.pass_obj
def logs(
    app: Application,
    name: str,
    display_name: str | None,
    metrics_prefix: str | None,
    platforms: str | None,
    location: str | None,
    quiet: bool,
    dry_run: bool,
    include_manifest: bool,
    skip_manifest: bool,
) -> None:
    """Scaffold a logs-only integration."""
    from ddev.cli.create._common import run_subcommand

    run_subcommand(
        app,
        integration_type='logs',
        name=name,
        display_name=display_name,
        metrics_prefix=metrics_prefix,
        platforms_csv=platforms,
        location=location,
        quiet=quiet,
        dry_run=dry_run,
        include_manifest=include_manifest,
        skip_manifest=skip_manifest,
    )
