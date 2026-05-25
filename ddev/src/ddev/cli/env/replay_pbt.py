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

import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path as StdPath
from typing import TYPE_CHECKING

import click

from ddev.replay_pbt.properties import REPLAY_PBT_PROPERTY_CHOICES

if TYPE_CHECKING:
    from ddev.cli.application import Application


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
    type=click.Choice(REPLAY_PBT_PROPERTY_CHOICES),
    help='Property to run. May be passed multiple times. Defaults to all properties.',
)
@click.option(
    '--check-class',
    help='Optional import spec for the check class, e.g. datadog_checks.cilium:CiliumCheck. Defaults to inference.',
)
@click.option('--old-env', 'old_hatch_env', help='Hatch env for the old side. Defaults to ENVIRONMENT.')
@click.option('--new-env', 'new_hatch_env', help='Hatch env for the new side. Defaults to ENVIRONMENT.')
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
    artifacts: StdPath | None,
    overwrite: bool,
) -> None:
    """Run cached replay PBT/metamorphic checks for one integration environment."""
    app: Application = ctx.obj
    selected_properties = properties or REPLAY_PBT_PROPERTY_CHOICES
    run_root = _resolve_replay_pbt_root(app.repo.path, artifacts, intg_name, environment, git_ref, overwrite)
    ddev_dir = StdPath(str(app.repo.path)) / 'ddev'

    app.display_header(f'Replay PBT: {intg_name}:{environment}')
    app.display_info(f'Writing replay-pbt artifacts to {run_root}')

    env = os.environ.copy()
    env.update(
        {
            'DDEV_REPLAY_PBT_INTEGRATION': intg_name,
            'DDEV_REPLAY_PBT_ENVIRONMENT': environment,
            'DDEV_REPLAY_PBT_CACHE': replay_cache,
            'DDEV_REPLAY_PBT_REF': git_ref,
            'DDEV_REPLAY_PBT_PROPERTIES': ','.join(selected_properties),
            'DDEV_REPLAY_PBT_ARTIFACTS': str(run_root),
        }
    )
    if check_class:
        env['DDEV_REPLAY_PBT_CHECK_CLASS'] = check_class
    if old_hatch_env:
        env['DDEV_REPLAY_PBT_OLD_ENV'] = old_hatch_env
    if new_hatch_env:
        env['DDEV_REPLAY_PBT_NEW_ENV'] = new_hatch_env

    app.platform.check_command(
        [sys.executable, '-m', 'pytest', 'tests/cli/env/test_replay_pbt.py'],
        cwd=ddev_dir,
        env=env,
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
