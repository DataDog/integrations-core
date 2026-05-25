# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Run property/metamorphic checks against cached integration replay artifacts.

This command is the user-facing entry point for testing a real integration with
adapter-saved replay data. It deliberately builds on ``compare-check`` cached
replay instead of starting E2E environments: first replay a cache through the
real check as a baseline, then optionally mutate a copy of the cache and assert
that evidence-backed invariants still hold over normalized check output.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path as StdPath
from typing import TYPE_CHECKING

import click
from datadog_checks.dev.replay.pbt.cache import copy_replay_cache, mutate_request_capture_label_order

from ddev.cli.env.compare_check import compare_check

if TYPE_CHECKING:
    from ddev.cli.application import Application

PROPERTY_DETERMINISTIC = 'deterministic'
PROPERTY_OPENMETRICS_LABEL_ORDER = 'openmetrics-label-order'
PROPERTIES = (PROPERTY_DETERMINISTIC, PROPERTY_OPENMETRICS_LABEL_ORDER)


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
    selected_properties = properties or PROPERTIES
    run_root = _resolve_replay_pbt_root(app.repo.path, artifacts, intg_name, environment, git_ref, overwrite)
    app.display_header(f'Replay PBT: {intg_name}:{environment}')
    app.display_info(f'Writing replay-pbt artifacts to {run_root}')

    summaries = []
    materialized_cache: StdPath | None = None
    baseline_normalized: dict | None = None

    if PROPERTY_DETERMINISTIC in selected_properties:
        first_dir = run_root / PROPERTY_DETERMINISTIC / 'first'
        second_dir = run_root / PROPERTY_DETERMINISTIC / 'second'
        _run_compare_check(
            ctx,
            intg_name=intg_name,
            environment=environment,
            git_ref=git_ref,
            replay_cache=replay_cache,
            check_class=check_class,
            old_hatch_env=old_hatch_env,
            new_hatch_env=new_hatch_env,
            artifacts=first_dir,
        )
        _run_compare_check(
            ctx,
            intg_name=intg_name,
            environment=environment,
            git_ref=git_ref,
            replay_cache=str(first_dir),
            check_class=check_class,
            old_hatch_env=old_hatch_env,
            new_hatch_env=new_hatch_env,
            artifacts=second_dir,
        )
        first_normalized = _read_normalized(first_dir)
        second_normalized = _read_normalized(second_dir)
        if first_normalized != second_normalized:
            raise click.ClickException('deterministic replay property failed: normalized outputs differ')
        materialized_cache = first_dir
        baseline_normalized = first_normalized
        summaries.append('deterministic: passed')

    if PROPERTY_OPENMETRICS_LABEL_ORDER in selected_properties:
        property_dir = run_root / PROPERTY_OPENMETRICS_LABEL_ORDER
        original_dir = property_dir / 'original'
        mutated_dir = property_dir / 'mutated'
        if materialized_cache is None or baseline_normalized is None:
            _run_compare_check(
                ctx,
                intg_name=intg_name,
                environment=environment,
                git_ref=git_ref,
                replay_cache=replay_cache,
                check_class=check_class,
                old_hatch_env=old_hatch_env,
                new_hatch_env=new_hatch_env,
                artifacts=original_dir,
            )
            materialized_cache = original_dir
            baseline_normalized = _read_normalized(original_dir)

        mutated_cache = property_dir / 'mutated-cache'
        copy_replay_cache(materialized_cache, mutated_cache)
        changed_records = mutate_request_capture_label_order(mutated_cache)
        if changed_records == 0:
            summaries.append('openmetrics-label-order: skipped (no reorderable request records)')
        else:
            _run_compare_check(
                ctx,
                intg_name=intg_name,
                environment=environment,
                git_ref=git_ref,
                replay_cache=str(mutated_cache),
                check_class=check_class,
                old_hatch_env=old_hatch_env,
                new_hatch_env=new_hatch_env,
                artifacts=mutated_dir,
            )
            mutated_normalized = _read_normalized(mutated_dir)
            if baseline_normalized != mutated_normalized:
                raise click.ClickException('openmetrics-label-order property failed: normalized outputs differ')
            summaries.append(f'openmetrics-label-order: passed ({changed_records} mutated records)')

    (run_root / 'summary.json').write_text(json.dumps({'properties': summaries}, indent=2, sort_keys=True) + '\n')
    for summary in summaries:
        app.display_success(summary)


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


def _run_compare_check(
    ctx: click.Context,
    *,
    intg_name: str,
    environment: str,
    git_ref: str,
    replay_cache: str,
    check_class: str | None,
    old_hatch_env: str | None,
    new_hatch_env: str | None,
    artifacts: StdPath,
) -> None:
    ctx.invoke(
        compare_check,
        intg_name=intg_name,
        environment=environment,
        old_ref=git_ref,
        new_ref=git_ref,
        check_class=check_class,
        artifacts=artifacts,
        exact_artifacts_dir=True,
        overwrite=True,
        replay_cache=replay_cache,
        old_hatch_env=old_hatch_env,
        new_hatch_env=new_hatch_env,
        comparison_mode='same-fixture-replay',
        recreate=False,
    )


def _read_normalized(run_dir: StdPath) -> dict:
    return json.loads((run_dir / 'new.normalized.json').read_text())


def _slug(value: str) -> str:
    import re

    value = re.sub(r'[^A-Za-z0-9_.-]+', '-', value).strip('-')
    return value[:60] or 'run'
