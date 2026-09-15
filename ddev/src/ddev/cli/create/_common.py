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
from typing import TYPE_CHECKING, Any, Callable

import click

from ddev.cli.create._naming import is_valid_integration_name, normalize_package_name

if TYPE_CHECKING:
    from ddev.cli.application import Application
    from ddev.cli.create._scaffold import CheckOnlyPrefillFields


def create_options(f: Callable[..., Any]) -> Callable[..., Any]:
    """Apply the full set of shared options (and the ``name`` argument) to a subcommand."""
    f = click.option(
        '--skip-manifest',
        is_flag=True,
        help='Do not require an existing `manifest.json` when using `check-only`.',
    )(f)
    f = click.option('--dry-run', '-n', is_flag=True, help='Only show what would be created.')(f)
    f = click.option('--location', '-l', default=None, help='The directory where files will be written.')(f)
    return click.argument('name')(f)


def dispatch(app: Application, *, integration_type: str, **options: Any) -> None:
    """Execute a create subcommand with its integration type."""
    run_subcommand(app, integration_type=integration_type, **options)


def run_subcommand(
    app: Application,
    *,
    integration_type: str,
    name: str,
    location: str | None,
    dry_run: bool,
    skip_manifest: bool,
) -> None:
    """Single entry point shared by all per-type subcommands."""
    _validate_integration_name(app, name)

    extra_fields: dict[str, Any] = {}
    target_integration_dir: str | None = None
    if integration_type == 'check_only':
        if skip_manifest:
            target_integration_dir = normalize_package_name(name)
            extra_fields['check_name'] = target_integration_dir
        else:
            # The existing manifest supplies check_name, the Python package name consumed by the scaffold.
            check_only_fields, target_integration_dir = _resolve_check_only_inputs(app, name, location)
            extra_fields.update(check_only_fields)

    from ddev.cli.create._scaffold import render

    render(
        app,
        integration_type,
        name,
        location=location,
        dry_run=dry_run,
        extra_fields=extra_fields,
        target_integration_dir=target_integration_dir,
    )


def _resolve_check_only_inputs(
    app: Application,
    name: str,
    location: str | None,
) -> tuple[CheckOnlyPrefillFields, str]:
    """For ``check_only`` integrations the directory must already exist with a manifest.

    Returns:
        - extra template fields prefilled from the existing manifest
        - the *target* integration directory name (the on-disk dir that holds the manifest;
          e.g. ``partner_thing`` for a ``partner_`` author prefix). The Python package
          name (``{check_name}``) comes from the prefilled fields, not from this value.
    """
    from ddev.cli.create._naming import normalize_display_name
    from ddev.cli.create._scaffold import prefill_check_only_fields
    from ddev.utils.fs import Path

    target_integration_dir = normalize_package_name(name)
    root = Path(location).resolve() if location else app.repo.path
    integration_dir = root / target_integration_dir
    manifest_path = integration_dir / 'manifest.json'

    if not manifest_path.is_file():
        app.abort(f'Expected {manifest_path} to exist')

    try:
        manifest_data = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        app.abort(f'Failed to read `{manifest_path}`: {exc}')

    if not isinstance(manifest_data, dict):
        app.abort(f'`{manifest_path}` does not contain a JSON object')

    author_raw = (manifest_data.get('author') or {}).get('name')
    author = (author_raw or '').strip() if isinstance(author_raw, str) else ''
    # Normalize first so an all-symbol author (e.g. "!@#$") collapses to "" and is rejected
    # by the same guard as a truly empty name. A passing value is non-empty and underscore-safe.
    author_normalized = normalize_display_name(author)
    if not author_normalized:
        app.abort('Unable to determine author from manifest')

    # `target_integration_dir` runs through `normalize_package_name`, which converts
    # hyphens to underscores. The author prefix must use the same normalization, or
    # a hyphenated author (e.g. "My-Partner") wouldn't match the underscore form in
    # the directory name, leaving the prefix in place and causing
    # `prefill_check_only_fields` to double the author segment downstream.
    author_pkg = normalize_package_name(author_normalized)
    stripped = target_integration_dir.removeprefix(f'{author_pkg}_')

    fields = prefill_check_only_fields(manifest_data, stripped, author_normalized)
    return fields, target_integration_dir


def _validate_integration_name(app: Application, name: str) -> None:
    """Reject names that would break path templating, package name normalization, or policy."""
    if not name:
        app.abort('Integration name must not be empty.')
    if not is_valid_integration_name(name):
        app.abort(
            f'Invalid integration name {name!r}. Names must contain only ASCII letters, digits, '
            "dots, hyphens, underscores, or spaces, and must begin and end with an alphanumeric character."
        )
    if name.lower().startswith('datadog'):
        app.abort('Integration names cannot start with `datadog`.')
