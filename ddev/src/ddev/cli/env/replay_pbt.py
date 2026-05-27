# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Thin CLI wrapper for cached integration replay validation.

The actual replay validation assertions live in pytest so they get normal test output,
Hypothesis integration, and focused failure reporting. This command only turns a
user-friendly `ddev env replay-pbt ...` invocation into a configured pytest run.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path as StdPath
from typing import TYPE_CHECKING

import click
from datadog_checks.dev.replay.pbt.properties import PROPERTIES

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command('replay-pbt', short_help='Run cached replay validations for an integration')
@click.argument('intg_name', metavar='INTEGRATION')
@click.argument('environment')
@click.option(
    '--replay-cache',
    default='auto',
    show_default=True,
    help='Existing compare-check artifact directory, or "auto"/"latest" for the selected integration environment.',
)
@click.option(
    '--target-ref',
    '--ref',
    'target_ref',
    default='HEAD',
    show_default=True,
    help='Git ref under test for replay-side execution.',
)
@click.option(
    '--fixture-ref',
    default=None,
    help=(
        'Git ref that produced the replay fixture. Defaults to the latest integration release tag, '
        'falling back to --target-ref.'
    ),
)
@click.option(
    '--property',
    'properties',
    multiple=True,
    type=click.Choice(PROPERTIES),
    help='Property to run. May be passed multiple times. Defaults to all properties.',
)
@click.option(
    '--check-class',
    help='Optional import spec for the check class, e.g. datadog_checks.cilium:CiliumCheck. Defaults to inference.',
)
@click.option(
    '--record-env',
    '--old-env',
    'record_hatch_env',
    help='Hatch env used for record-side execution. Defaults to ENVIRONMENT.',
)
@click.option(
    '--replay-env',
    '--new-env',
    'replay_hatch_env',
    help='Hatch env used for replay-side execution. Defaults to ENVIRONMENT.',
)
@click.option(
    '--readings', default=2, show_default=True, type=click.IntRange(min=1), help='Number of check readings to replay.'
)
@click.option(
    '--artifacts',
    type=click.Path(file_okay=False, path_type=StdPath),
    help='Exact artifact root for this replay validation run. Defaults to .ddev/replay-pbt under the repository root.',
)
@click.option('--overwrite', is_flag=True, help='Remove an existing --artifacts directory before writing.')
@click.option(
    '--check-cache-only', is_flag=True, help='Validate replay-cache suitability and exit without running tests.'
)
@click.option('--adapters', default='all', show_default=True, help='Comma-separated replay adapters, or "all".')
@click.option('--warnings-as-errors', is_flag=True, help='Promote replay validation advisory warnings to test failures.')
@click.pass_context
def replay_pbt(
    ctx: click.Context,
    *,
    intg_name: str,
    environment: str,
    replay_cache: str,
    target_ref: str,
    fixture_ref: str | None,
    properties: tuple[str, ...],
    check_class: str | None,
    record_hatch_env: str | None,
    replay_hatch_env: str | None,
    readings: int,
    artifacts: StdPath | None,
    overwrite: bool,
    check_cache_only: bool,
    adapters: str,
    warnings_as_errors: bool,
) -> None:
    """Run cached replay validation and metamorphic checks for one integration environment."""
    app: Application = ctx.obj
    selected_properties = properties or PROPERTIES
    effective_fixture_ref = fixture_ref or _latest_integration_release_tag(app.repo.path, intg_name) or target_ref
    if fixture_ref is None:
        app.display_info(f'Using fixture ref: {effective_fixture_ref}')
    if check_cache_only:
        resolved_cache = _check_replay_cache(
            app,
            intg_name=intg_name,
            environment=environment,
            replay_cache=replay_cache,
            fixture_ref=effective_fixture_ref,
            target_ref=target_ref,
            record_hatch_env=record_hatch_env,
            replay_hatch_env=replay_hatch_env,
            check_class=check_class,
            readings=readings,
            adapters=adapters,
        )
        app.display_success(f'Replay cache is suitable: {resolved_cache}')
        return

    run_root = _resolve_replay_pbt_root(app.repo.path, artifacts, intg_name, environment, target_ref, overwrite)
    ddev_dir = StdPath(str(app.repo.path)) / 'ddev'

    app.display_header(f'Replay validation: {intg_name}:{environment}')
    app.display_info(f'Writing replay validation artifacts to {run_root}')

    config_path = run_root / 'replay-pbt-config.json'
    config = {
        'integration': intg_name,
        'environment': environment,
        'replay_cache': replay_cache,
        'fixture_ref': effective_fixture_ref,
        'target_ref': target_ref,
        # Backward-compatible key for older direct pytest invocations.
        'ref': target_ref,
        'properties': list(selected_properties),
        'artifacts': str(run_root),
        'repo': str(app.repo.path),
        'readings': readings,
        'check_class': check_class,
        'adapters': adapters,
        'warnings_as_errors': warnings_as_errors,
        'record_env': record_hatch_env,
        'replay_env': replay_hatch_env,
        # Backward-compatible keys for older direct pytest invocations.
        'old_env': record_hatch_env,
        'new_env': replay_hatch_env,
    }
    config_path.write_text(json.dumps(config, indent=2, sort_keys=True) + '\n')

    env = {**os.environ, 'DDEV_REPLAY_PBT_CONFIG': str(config_path)}
    app.platform.check_command(
        [
            sys.executable,
            '-m',
            'pytest',
            '--noconftest',
            'tests/cli/env/test_replay_pbt.py',
            'tests/cli/env/test_replay_static_contracts.py',
        ],
        cwd=ddev_dir,
        env=env,
    )


def _latest_integration_release_tag(repo_path, integration: str) -> str | None:
    try:
        tags = subprocess.check_output(
            ['git', '-C', str(repo_path), 'tag', '--list', f'{integration}-*', '--sort=-v:refname'],
            text=True,
        ).splitlines()
    except subprocess.CalledProcessError:
        return None

    return tags[0] if tags else None


def _check_replay_cache(
    app: Application,
    *,
    intg_name: str,
    environment: str,
    replay_cache: str,
    fixture_ref: str,
    target_ref: str,
    record_hatch_env: str | None,
    replay_hatch_env: str | None,
    check_class: str | None,
    readings: int,
    adapters: str,
) -> StdPath | None:
    from ddev.cli.env.compare_check import _git_rev_parse, _resolve_replay_cache

    record_head = _git_rev_parse(app.repo.path, fixture_ref)
    replay_head = _git_rev_parse(app.repo.path, target_ref)
    return _resolve_replay_cache(
        app.repo.path,
        intg_name,
        environment,
        replay_cache,
        adapters,
        record_hatch_env or environment,
        replay_hatch_env or environment,
        'same-fixture-replay',
        record_head=record_head,
        replay_head=replay_head,
        check_class=check_class,
        readings=readings,
    )


def _resolve_replay_pbt_root(
    repo_path, artifacts: StdPath | None, integration: str, environment: str, git_ref: str, overwrite: bool
) -> StdPath:
    if artifacts is None:
        run_id = f'{datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")}-{_slug(git_ref)}'
        run_root = StdPath(str(repo_path)) / '.ddev' / 'replay-pbt' / integration / environment / run_id
    else:
        run_root = artifacts

    if run_root.exists():
        if not overwrite:
            raise click.ClickException(
                f'Artifacts directory already exists: {run_root}. Use --overwrite to replace it.'
            )
        shutil.rmtree(run_root)
    run_root.mkdir(parents=True)
    return run_root


def _slug(value: str) -> str:
    import re

    value = re.sub(r'[^A-Za-z0-9_.-]+', '-', value).strip('-')
    return value[:60] or 'run'
