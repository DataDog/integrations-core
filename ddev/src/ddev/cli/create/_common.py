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
    from ddev.utils.fs import Path

SUPPORTED_PLATFORMS = ('linux', 'windows', 'mac_os')


def create_options(f: Callable[..., Any]) -> Callable[..., Any]:
    """Apply the full set of shared options (and the ``name`` argument) to a subcommand."""
    f = click.option(
        '--skip-manifest',
        is_flag=True,
        help='[DEPRECATED] No-op; manifest-less is now the default. Use `--include-manifest` to opt back in.',
    )(f)
    f = click.option(
        '--include-manifest',
        is_flag=True,
        help='Generate a `manifest.json` (legacy behaviour).',
    )(f)
    f = click.option('--dry-run', '-n', is_flag=True, help='Only show what would be created.')(f)
    f = click.option('--location', '-l', default=None, help='The directory where files will be written.')(f)
    f = click.option('--platforms', default=None, help='Comma-separated list of `linux,windows,mac_os`.')(f)
    f = click.option('--metrics-prefix', default=None, help='Metric namespace (e.g. `myintegration.`).')(f)
    f = click.option('--display-name', default=None, help='Human-readable display name for the integration.')(f)
    return click.argument('name')(f)


def dispatch(app: Application, *, integration_type: str, **options: Any) -> None:
    """Translate click kwargs to ``run_subcommand`` parameters and execute.

    The factory binds the click flag ``--platforms`` to a kwarg named ``platforms``;
    ``run_subcommand`` takes it as ``platforms_csv``. This wrapper does that one
    rename so the per-subcommand files can ``**options``-through without thinking
    about parameter names.
    """
    platforms_csv = options.pop('platforms', None)
    run_subcommand(app, integration_type=integration_type, platforms_csv=platforms_csv, **options)


def run_subcommand(
    app: Application,
    *,
    integration_type: str,
    name: str,
    display_name: str | None,
    metrics_prefix: str | None,
    platforms_csv: str | None,
    location: str | None,
    dry_run: bool,
    include_manifest: bool,
    skip_manifest: bool,
) -> None:
    """Single entry point shared by all per-type subcommands."""
    _validate_integration_name(app, name)

    if skip_manifest and include_manifest:
        app.abort('`--skip-manifest` and `--include-manifest` are mutually exclusive.')

    if skip_manifest:
        app.display_warning(
            '`--skip-manifest` is deprecated. The default for new integrations no longer '
            'includes a `manifest.json`; pass `--include-manifest` to opt in. '
            '`--skip-manifest` will be removed in the next major release.'
        )

    extra_fields: CheckOnlyPrefillFields | dict[str, object] = {}
    target_integration_dir: str | None = None
    if integration_type == 'check_only':
        # Read unconditionally (even with --include-manifest): the manifest supplies check_name,
        # the Python package name consumed by both the manifest-less and manifest paths.
        extra_fields, target_integration_dir = _resolve_check_only_inputs(app, name, location)

    from ddev.cli.create._scaffold import render

    render_kwargs: dict[str, Any] = {
        'location': location,
        'dry_run': dry_run,
        'include_manifest': include_manifest,
        'extra_fields': extra_fields,
        'target_integration_dir': target_integration_dir,
    }

    if include_manifest:
        render(app, integration_type, name, **render_kwargs)
        return

    # Manifest-less path: resolve overrides and probe config writability before scaffolding
    # so a malformed config aborts cleanly instead of leaving a half-finished integration on disk.
    _probe_repo_config_readable(app)
    resolved_display_name, resolved_metrics_prefix, resolved_platforms = _resolve_manifestless_inputs(
        app,
        name=name,
        display_name=display_name,
        metrics_prefix=metrics_prefix,
        platforms_csv=platforms_csv,
    )

    result = render(app, integration_type, name, **render_kwargs)

    if dry_run:
        return

    _write_manifestless_overrides(
        app,
        integration_dir=result.integration_dir,
        override_dir_name=target_integration_dir or result.integration_dir.name,
        display_name=resolved_display_name,
        metrics_prefix=resolved_metrics_prefix,
        platforms=resolved_platforms,
    )


def _write_manifestless_overrides(
    app: Application,
    *,
    integration_dir: Path,
    override_dir_name: str,
    display_name: str,
    metrics_prefix: str,
    platforms: list[str],
) -> None:
    from ddev.cli.create._config_overrides import apply_manifestless_overrides

    try:
        apply_manifestless_overrides(
            app,
            dir_name=override_dir_name,
            display_name=display_name,
            metrics_prefix=metrics_prefix,
            platforms=platforms,
        )
    except OSError as exc:
        # markup=False: the TOML section headers ([overrides.display-name], ...) would
        # otherwise be parsed by Rich as style tags and stripped from the output, leaving
        # the user with copy-paste instructions missing their section headers.
        app.abort(
            f'Failed to update `.ddev/config.toml`: {exc}\n'
            f'The integration was scaffolded at `{integration_dir}` but the '
            f'overrides were not recorded. Add these entries by hand:\n'
            f'  [overrides.display-name]\n'
            f'  {override_dir_name} = "{display_name}"\n'
            f'  [overrides.metrics-prefix]\n'
            f'  {override_dir_name} = "{metrics_prefix}"\n'
            f'  [overrides.manifest.platforms]\n'
            f'  {override_dir_name} = {platforms!r}',
            markup=False,
        )


def _probe_repo_config_readable(app: Application) -> None:
    """Ensure ``.ddev/config.toml`` can be loaded before we start scaffolding."""
    config_file = app.repo.config
    if not config_file.path.is_file():
        return
    try:
        config_file.load_data()
    except (OSError, ValueError) as exc:
        app.abort(f'Failed to read `{config_file.path}`: {exc}. Fix or remove the file before creating an integration.')


def _resolve_manifestless_inputs(
    app: Application,
    *,
    name: str,
    display_name: str | None,
    metrics_prefix: str | None,
    platforms_csv: str | None,
) -> tuple[str, str, list[str]]:
    suggested_display = name
    suggested_prefix = f'{normalize_package_name(name)}.'
    suggested_platforms_csv = ','.join(SUPPORTED_PLATFORMS)

    missing: list[str] = []
    if display_name is None:
        if app.interactive:
            display_name = app.prompt('Display name', default=suggested_display)
        else:
            missing.append('--display-name')
    if metrics_prefix is None:
        if app.interactive:
            metrics_prefix = app.prompt('Metrics prefix', default=suggested_prefix)
        else:
            missing.append('--metrics-prefix')
    if platforms_csv is None:
        if app.interactive:
            platforms_csv = app.prompt('Platforms (comma-separated)', default=suggested_platforms_csv)
        else:
            missing.append('--platforms')

    if missing:
        app.abort(
            'Missing required flag(s) while running with `--no-interactive` (or in a non-TTY '
            'environment): ' + ', '.join(missing)
        )

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
