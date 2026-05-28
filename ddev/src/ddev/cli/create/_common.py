# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Shared subcommand implementation for the ``ddev create`` group.

The per-type subcommand modules (``check.py``, ``jmx.py``, ...) are kept
deliberately thin so that ``ddev create --help`` doesn't trigger any heavy
imports. All real work lives here, behind a lazy import.
"""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING

from ddev.cli.create._naming import normalize_package_name

if TYPE_CHECKING:
    from ddev.cli.application import Application

SUPPORTED_PLATFORMS = ('linux', 'windows', 'mac_os')


def run_subcommand(
    app: Application,
    *,
    integration_type: str,
    name: str,
    display_name: str | None,
    metrics_prefix: str | None,
    platforms_csv: str | None,
    location: str | None,
    quiet: bool,
    dry_run: bool,
    include_manifest: bool,
    skip_manifest: bool,
) -> None:
    """Single entry point shared by all per-type subcommands."""
    if name.lower().startswith('datadog'):
        app.abort('Integration names cannot start with `datadog`.')

    if skip_manifest and include_manifest:
        app.abort('`--skip-manifest` and `--include-manifest` are mutually exclusive.')

    if skip_manifest:
        app.display_warning(
            '`--skip-manifest` is deprecated. The default for new integrations no longer '
            'includes a `manifest.json`; pass `--include-manifest` to opt in. '
            '`--skip-manifest` will be removed in the next major release.'
        )

    is_interactive = sys.stdin.isatty()

    extra_fields: dict[str, object] = {}
    override_integration_dir_name: str | None = None
    if integration_type == 'check_only':
        extra_fields, override_integration_dir_name = _resolve_check_only_inputs(
            app, name, location, include_manifest=include_manifest
        )

    resolved_display_name: str | None = None
    resolved_metrics_prefix: str | None = None
    resolved_platforms: list[str] | None = None
    if not include_manifest:
        resolved_display_name, resolved_metrics_prefix, resolved_platforms = _resolve_manifestless_inputs(
            app,
            name=name,
            display_name=display_name,
            metrics_prefix=metrics_prefix,
            platforms_csv=platforms_csv,
            is_interactive=is_interactive,
        )

    from ddev.cli.create._scaffold import render

    result = render(
        app,
        integration_type,
        name,
        location=location,
        dry_run=dry_run,
        quiet=quiet,
        include_manifest=include_manifest,
        extra_fields=extra_fields,
        override_integration_dir_name=override_integration_dir_name,
    )

    if dry_run or include_manifest:
        return

    if not include_manifest:
        from ddev.cli.create._config_overrides import apply_manifestless_overrides

        # mypy: these are non-None because _resolve_manifestless_inputs aborts otherwise.
        assert resolved_display_name is not None
        assert resolved_metrics_prefix is not None
        assert resolved_platforms is not None

        apply_manifestless_overrides(
            app,
            dir_name=result.integration_dir.name,
            display_name=resolved_display_name,
            metrics_prefix=resolved_metrics_prefix,
            platforms=resolved_platforms,
        )


def _resolve_manifestless_inputs(
    app: Application,
    *,
    name: str,
    display_name: str | None,
    metrics_prefix: str | None,
    platforms_csv: str | None,
    is_interactive: bool,
) -> tuple[str, str, list[str]]:
    suggested_display = name
    suggested_prefix = f'{normalize_package_name(name)}.'
    suggested_platforms_csv = ','.join(SUPPORTED_PLATFORMS)

    missing: list[str] = []
    if display_name is None:
        if is_interactive:
            display_name = app.prompt('Display name', default=suggested_display)
        else:
            missing.append('--display-name')
    if metrics_prefix is None:
        if is_interactive:
            metrics_prefix = app.prompt('Metrics prefix', default=suggested_prefix)
        else:
            missing.append('--metrics-prefix')
    if platforms_csv is None:
        if is_interactive:
            platforms_csv = app.prompt('Platforms (comma-separated)', default=suggested_platforms_csv)
        else:
            missing.append('--platforms')

    if missing:
        app.abort('Missing required flags for non-interactive mode: ' + ', '.join(missing))

    assert display_name is not None
    assert metrics_prefix is not None
    assert platforms_csv is not None
    platforms = _parse_platforms(app, platforms_csv)
    return display_name, metrics_prefix, platforms


def _parse_platforms(app: Application, csv: str) -> list[str]:
    items = [p.strip() for p in csv.split(',') if p.strip()]
    if not items:
        app.abort('`--platforms` must contain at least one platform.')
    unknown = [p for p in items if p not in SUPPORTED_PLATFORMS]
    if unknown:
        app.abort(f'Unknown platform(s): {", ".join(unknown)}. Valid values: {", ".join(SUPPORTED_PLATFORMS)}.')
    return items


def _resolve_check_only_inputs(
    app: Application,
    name: str,
    location: str | None,
    *,
    include_manifest: bool,
) -> tuple[dict[str, object], str | None]:
    """For ``check_only`` integrations we expect the directory to already exist with a manifest.

    Returns the extra template fields prefilled from the existing manifest, plus
    the override directory name (with the author prefix stripped).
    """
    from ddev.cli.create._scaffold import prefill_check_only_fields
    from ddev.utils.fs import Path

    integration_dir_name = normalize_package_name(name)
    root = Path(location).resolve() if location else app.repo.path
    integration_dir = root / integration_dir_name
    manifest_path = integration_dir / 'manifest.json'

    if not manifest_path.is_file():
        app.abort(f'Expected {manifest_path} to exist')

    manifest_data = json.loads(manifest_path.read_text())
    author = (manifest_data.get('author') or {}).get('name')
    if author is None:
        app.abort('Unable to determine author from manifest')

    from ddev.cli.create._naming import normalize_display_name

    author_normalized = normalize_display_name(author)
    stripped = integration_dir_name.removeprefix(f'{author_normalized}_')

    fields = prefill_check_only_fields(manifest_data, stripped)
    return fields, stripped
