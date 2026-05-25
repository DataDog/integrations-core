# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Thin CLI wrapper for cached integration replay property tests.

The actual replay-PBT assertions live in pytest so they get normal test output,
Hypothesis integration, and focused failure reporting. This command only turns a
user-friendly `ddev env replay-pbt ...` invocation into a configured pytest run
against the integration replay-PBT test module.
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path as StdPath
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


PROPERTIES = (
    'deterministic',
    'openmetrics-label-order',
    'openmetrics-comments-blank-lines',
    'openmetrics-final-newline',
    'openmetrics-help-text',
    'openmetrics-help-removal',
    'metadata-emitted-metrics',
    'output-finite-values',
    'rate-finite-values',
    'monotonic-count-nonnegative',
)


@click.command('replay-pbt', short_help='Run cached replay property checks for an integration')
@click.argument('intg_name', metavar='INTEGRATION')
@click.argument('environment')
@click.option(
    '--replay-cache',
    required=True,
    help='Existing compare-check artifact directory, or "auto"/"latest" for the selected integration environment.',
)
@click.option('--ref', 'git_ref', default='HEAD', show_default=True, help='Git ref to replay on both sides.')
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
@click.option('--old-env', 'old_hatch_env', help='Hatch env for the old side. Defaults to ENVIRONMENT.')
@click.option('--new-env', 'new_hatch_env', help='Hatch env for the new side. Defaults to ENVIRONMENT.')
@click.option(
    '--readings', default=1, show_default=True, type=click.IntRange(min=1), help='Number of check readings to replay.'
)
@click.option(
    '--artifacts',
    type=click.Path(file_okay=False, path_type=StdPath),
    help='Exact artifact root for this replay-pbt run. Defaults to .ddev/replay-pbt under the repository root.',
)
@click.option('--overwrite', is_flag=True, help='Remove an existing --artifacts directory before writing.')
@click.pass_context
def replay_pbt(
    ctx: click.Context,
    *,
    intg_name: str,
    environment: str,
    replay_cache: str,
    git_ref: str,
    properties: tuple[str, ...],
    check_class: str | None,
    old_hatch_env: str | None,
    new_hatch_env: str | None,
    readings: int,
    artifacts: StdPath | None,
    overwrite: bool,
) -> None:
    """Run cached replay PBT/metamorphic checks for one integration environment."""
    app: Application = ctx.obj
    selected_properties = properties or PROPERTIES
    run_root = _resolve_replay_pbt_root(app.repo.path, artifacts, intg_name, environment, git_ref, overwrite)
    ddev_dir = StdPath(str(app.repo.path)) / 'ddev'

    app.display_header(f'Replay PBT: {intg_name}:{environment}')
    app.display_info(f'Writing replay-pbt artifacts to {run_root}')

    config_path = run_root / 'replay-pbt-config.json'
    config = {
        'integration': intg_name,
        'environment': environment,
        'replay_cache': replay_cache,
        'ref': git_ref,
        'properties': list(selected_properties),
        'artifacts': str(run_root),
        'repo': str(app.repo.path),
        'readings': readings,
        'check_class': check_class,
        'old_env': old_hatch_env,
        'new_env': new_hatch_env,
    }
    config_path.write_text(json.dumps(config, indent=2, sort_keys=True) + '\n')

    app.platform.check_command(
        [
            sys.executable,
            '-m',
            'pytest',
            'tests/cli/env/test_replay_pbt.py',
            '--replay-pbt-config',
            str(config_path),
        ],
        cwd=ddev_dir,
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
