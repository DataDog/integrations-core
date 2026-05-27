# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from functools import partial
from pathlib import Path as StdPath
from typing import TYPE_CHECKING

import click
from datadog_checks.dev.replay.redaction import scrub_json, scrub_output

if TYPE_CHECKING:
    from ddev.cli.application import Application


# Manual cache invalidation knob for compare-check artifacts. Bump this whenever
# replay fixture semantics or suitability criteria change in a way that should
# make existing .ddev/replay caches ineligible for --replay-cache auto/latest.
REPLAY_CACHE_VERSION = 5
REPLAY_ADAPTER = 'all'
OUTPUT_COLLECTIONS = (
    'metrics',
    'service_checks',
    'events',
    'metadata',
    'external_tags',
    'persistent_cache',
    'agent_logs',
    'telemetry',
    'adapter_stats',
)


@click.command('compare-check', short_help='Compare no-Agent check output across two refs')
@click.argument('intg_name', metavar='INTEGRATION')
@click.argument('environment', required=False)
@click.option(
    '--record-ref',
    '--old-ref',
    'record_ref',
    required=True,
    help='Git ref used to record fixture input and produce record-side output.',
)
@click.option(
    '--replay-ref',
    '--new-ref',
    'replay_ref',
    help='Git ref used to replay fixture input and produce replay-side output. Defaults to the current working tree.',
)
@click.option(
    '--check-class',
    help='Optional import spec for the check class, e.g. datadog_checks.cilium:CiliumCheck. Defaults to inference.',
)
@click.option(
    '--artifacts',
    type=click.Path(file_okay=False, path_type=StdPath),
    help='Artifact root. Defaults to .ddev/replay under the repository root.',
)
@click.option(
    '--exact-artifacts-dir',
    is_flag=True,
    help='Treat --artifacts as the exact run directory instead of creating a timestamped child directory.',
)
@click.option('--overwrite', is_flag=True, help='Remove an existing exact artifacts directory before writing.')
@click.option(
    '--replay-cache',
    help=(
        'Existing compare-check artifact directory to replay from instead of recording live input. '
        'Use "auto" or "latest" to find the newest suitable default artifact for each selected environment.'
    ),
)
@click.option(
    '--record-env',
    '--old-env',
    'record_hatch_env',
    help='Hatch env used for record-side execution. Defaults to the selected fixture environment.',
)
@click.option(
    '--replay-env',
    '--new-env',
    'replay_hatch_env',
    help='Hatch env used for replay-side execution. Defaults to the selected fixture environment.',
)
@click.option(
    '--comparison-mode',
    default='same-fixture-replay',
    show_default=True,
    type=click.Choice(['same-fixture-replay', 'record-each-side']),
    help='Use one recorded fixture for both sides, or record each side from its own environment.',
)
@click.option('--recreate', '-r', is_flag=True, help='Recreate the environment before comparing')
@click.option(
    '--readings',
    default=1,
    show_default=True,
    type=click.IntRange(min=1),
    help='Number of check readings to record/replay.',
)
@click.option(
    '--replay-time',
    default=1_700_000_000.0,
    show_default=True,
    type=float,
    help='Logical Unix time injected into check replay runs.',
)
@click.option(
    '--reading-interval',
    default=15.0,
    show_default=True,
    type=float,
    help='Logical seconds between check readings.',
)
@click.option(
    '--adapters',
    default=REPLAY_ADAPTER,
    show_default=True,
    help='Comma-separated replay adapters to record/replay, or "all".',
)
@click.pass_context
def compare_check(
    ctx: click.Context,
    *,
    intg_name: str,
    environment: str | None,
    record_ref: str,
    replay_ref: str | None,
    check_class: str | None,
    artifacts: StdPath | None,
    exact_artifacts_dir: bool,
    overwrite: bool,
    replay_cache: str | None,
    record_hatch_env: str | None,
    replay_hatch_env: str | None,
    comparison_mode: str,
    recreate: bool,
    readings: int,
    replay_time: float,
    reading_interval: float,
    adapters: str,
):
    """
    Compare no-Agent check output across two integrations-core refs.

    This implementation records input from RECORD_REF and replays it to REPLAY_REF
    through isolated Hatch environments.
    """
    from ddev.e2e.config import EnvDataStorage

    app: Application = ctx.obj
    integration = app.repo.integrations.get(intg_name)
    adapter = adapters
    storage = EnvDataStorage(app.data_dir)
    if comparison_mode == 'record-each-side':
        if environment is not None:
            raise click.ClickException('record-each-side mode uses --record-env/--replay-env; omit ENVIRONMENT.')
        if not record_hatch_env or not replay_hatch_env:
            raise click.ClickException('record-each-side mode requires both --record-env and --replay-env.')
        env_names = [f'{record_hatch_env}__vs__{replay_hatch_env}']
    else:
        env_names = _select_env_names(ctx, integration, storage, environment)
        if not env_names:
            app.display_info(f"Selected target {integration.name!r} has no matching E2E environments.")
            return

    replay_cache_auto = replay_cache in ('auto', 'latest')
    if replay_cache and not replay_cache_auto and len(env_names) > 1:
        raise click.ClickException(
            '--replay-cache can only use an explicit artifact directory with one selected environment.'
        )

    batch_results = []
    for env_name in env_names:
        app.display_header(f'{integration.display_name}: {env_name}')
        effective_record_env = record_hatch_env or env_name
        effective_replay_env = replay_hatch_env or env_name
        record_head = _git_rev_parse(app.repo.path, record_ref)
        replay_head = _git_rev_parse(app.repo.path, replay_ref or 'HEAD')
        resolved_replay_cache = _resolve_replay_cache(
            app.repo.path,
            integration.name,
            env_name,
            replay_cache,
            adapter,
            effective_record_env,
            effective_replay_env,
            comparison_mode,
            record_head=record_head,
            replay_head=replay_head,
            check_class=check_class,
            readings=readings,
        )
        if replay_cache_auto:
            app.display_info(f'Using replay cache: {resolved_replay_cache}')

        run_dir, diff = _compare_one_environment(
            ctx=ctx,
            integration=integration,
            environment=env_name,
            storage=storage,
            record_ref=record_ref,
            replay_ref=replay_ref,
            record_head=record_head,
            replay_head=replay_head,
            check_class=check_class,
            artifacts=artifacts,
            exact_artifacts_dir=exact_artifacts_dir,
            overwrite=overwrite,
            replay_cache=resolved_replay_cache,
            adapter=adapter,
            record_hatch_env=effective_record_env,
            replay_hatch_env=effective_replay_env,
            comparison_mode=comparison_mode,
            recreate=recreate,
            readings=readings,
            replay_time=replay_time,
            reading_interval=reading_interval,
        )
        batch_results.append((env_name, run_dir, diff))
        app.display_success(f'Wrote compare-check artifacts to {run_dir}')
        app.display_info(_format_diff_summary(diff))

    if len(batch_results) > 1:
        app.display_header('compare-check summary')
        for env_name, run_dir, diff in batch_results:
            app.display_info(f'{env_name}: {_format_diff_summary(diff)} ({run_dir})')

    changed_envs = [env_name for env_name, _, diff in batch_results if diff.get('changed')]
    if changed_envs:
        raise click.ClickException(f'compare-check detected differences or incomplete runs: {", ".join(changed_envs)}')


def _select_env_names(ctx: click.Context, integration, storage, environment: str | None) -> list[str]:
    from ddev.cli.env.test import is_e2e_environment, is_selected_environment, uses_platform, uses_python_version
    from ddev.utils.ci import running_in_ci
    from ddev.utils.hatch import list_environment_names

    app: Application = ctx.obj
    active_envs = storage.get_environments(integration.name)
    if environment is None:
        environment = 'all' if (not active_envs or running_in_ci()) else 'active'

    if environment == 'active':
        return active_envs

    return list_environment_names(
        app.platform,
        integration,
        filters=[
            is_e2e_environment,
            partial(uses_python_version, python_filter=None),
            partial(uses_platform, platform=app.platform.name),
            partial(is_selected_environment, environment_name=environment),
        ],
    )


def _compare_one_environment(
    *,
    ctx: click.Context,
    integration,
    environment: str,
    storage,
    record_ref: str,
    replay_ref: str | None,
    record_head: str,
    replay_head: str,
    check_class: str | None,
    artifacts: StdPath | None,
    exact_artifacts_dir: bool,
    overwrite: bool,
    replay_cache: StdPath | None,
    adapter: str,
    record_hatch_env: str,
    replay_hatch_env: str,
    comparison_mode: str,
    recreate: bool,
    readings: int,
    replay_time: float,
    reading_interval: float,
) -> tuple[StdPath, dict]:
    app: Application = ctx.obj
    run_dir = _resolve_artifacts_dir(
        app.repo.path,
        artifacts,
        integration.name,
        environment,
        replay_ref or 'working-tree',
        exact_artifacts_dir,
        overwrite,
    )

    phase = 'artifact_setup'
    started_envs: list[str] = []
    record_returncode = None
    replay_returncode = None
    refs: dict = {}
    record_mode = 'replay' if replay_cache else 'record'
    replay_mode = None
    same_fixture = comparison_mode == 'same-fixture-replay'
    fixture_env = environment if same_fixture else None
    replay_cache_provenance = _replay_cache_provenance(app.repo.path, integration.name, environment, replay_cache)
    try:
        replay_ref_label = replay_ref or 'working-tree'
        refs = {
            'record_ref': record_ref,
            'record_head': record_head,
            'replay_ref': replay_ref_label,
            'replay_head': replay_head,
            'replay_dirty': _git_dirty(app.repo.path),
            'fixture_env': fixture_env,
            'record_env': record_hatch_env,
            'replay_env': replay_hatch_env,
            'comparison_mode': comparison_mode,
            'same_fixture': same_fixture,
            'record_source': 'cache' if replay_cache else 'live',
            'replay_cache': replay_cache_provenance,
            'adapter': adapter,
            'check_class': check_class,
            'cache_version': REPLAY_CACHE_VERSION,
            'readings': readings,
            'replay_time': replay_time,
            'reading_interval': reading_interval,
        }
        (run_dir / 'refs.json').write_text(json.dumps(refs, indent=2, sort_keys=True) + '\n')

        phase = 'worktree_setup'
        with tempfile.TemporaryDirectory(prefix='compare-check-') as temp_dir:
            temp_path = StdPath(temp_dir)
            record_tree = temp_path / 'record'
            _git_worktree(app.repo.path, record_ref, record_tree)
            if replay_ref:
                replay_tree = temp_path / 'replay'
                _git_worktree(app.repo.path, replay_ref, replay_tree)
            else:
                replay_tree = StdPath(str(app.repo.path))

            if replay_cache:
                phase = 'cache_setup'
                if same_fixture:
                    _copy_cache_file(replay_cache, run_dir, 'config.json')
                    _copy_fixture_bundle(replay_cache, run_dir, 'capture.json')

                    phase = 'record_run'
                    record_returncode = _run_hatch(
                        repo=record_tree,
                        platform_repo=StdPath(str(app.repo.path)),
                        artifacts=run_dir,
                        integration=integration.name,
                        hatch_env=record_hatch_env,
                        check_name=integration.name,
                        check_class=check_class,
                        mode='replay',
                        adapter=adapter,
                        config_name='config.json',
                        fixture_name='capture.json',
                        output_name='record.raw.json',
                        readings=readings,
                        replay_time=replay_time,
                        reading_interval=reading_interval,
                    )

                    replay_mode = 'replay'
                    phase = 'replay_run'
                    replay_returncode = _run_hatch(
                        repo=replay_tree,
                        platform_repo=StdPath(str(app.repo.path)),
                        artifacts=run_dir,
                        integration=integration.name,
                        hatch_env=replay_hatch_env,
                        check_name=integration.name,
                        check_class=check_class,
                        mode='replay',
                        adapter=adapter,
                        config_name='config.json',
                        fixture_name='capture.json',
                        output_name='replay.raw.json',
                        readings=readings,
                        replay_time=replay_time,
                        reading_interval=reading_interval,
                    )
                else:
                    _copy_cache_file(replay_cache, run_dir, 'record.config.json')
                    _copy_fixture_bundle(replay_cache, run_dir, 'capture.json')
                    _copy_cache_file(replay_cache, run_dir, 'replay.config.json')
                    _copy_fixture_bundle(replay_cache, run_dir, 'replay.capture.json')

                    phase = 'record_run'
                    record_returncode = _run_hatch(
                        repo=record_tree,
                        platform_repo=StdPath(str(app.repo.path)),
                        artifacts=run_dir,
                        integration=integration.name,
                        hatch_env=record_hatch_env,
                        check_name=integration.name,
                        check_class=check_class,
                        mode='replay',
                        adapter=adapter,
                        config_name='record.config.json',
                        fixture_name='capture.json',
                        output_name='record.raw.json',
                        readings=readings,
                        replay_time=replay_time,
                        reading_interval=reading_interval,
                    )

                    replay_mode = 'replay'
                    phase = 'replay_run'
                    replay_returncode = _run_hatch(
                        repo=replay_tree,
                        platform_repo=StdPath(str(app.repo.path)),
                        artifacts=run_dir,
                        integration=integration.name,
                        hatch_env=replay_hatch_env,
                        check_name=integration.name,
                        check_class=check_class,
                        mode='replay',
                        adapter=adapter,
                        config_name='replay.config.json',
                        fixture_name='replay.capture.json',
                        output_name='replay.raw.json',
                        readings=readings,
                        replay_time=replay_time,
                        reading_interval=reading_interval,
                    )
            elif same_fixture:
                assert fixture_env is not None
                phase = 'environment_setup'
                if _ensure_environment(ctx, integration, storage, fixture_env, recreate):
                    started_envs.append(fixture_env)

                config = storage.get(integration.name, fixture_env).read_config()
                (run_dir / 'config.json').write_text(json.dumps(config, indent=2, sort_keys=True) + '\n')

                phase = 'record_run'
                record_returncode = _run_hatch(
                    repo=record_tree,
                    platform_repo=StdPath(str(app.repo.path)),
                    artifacts=run_dir,
                    integration=integration.name,
                    hatch_env=record_hatch_env,
                    check_name=integration.name,
                    check_class=check_class,
                    mode='record',
                    adapter=adapter,
                    config_name='config.json',
                    fixture_name='capture.json',
                    output_name='record.raw.json',
                    readings=readings,
                    replay_time=replay_time,
                    reading_interval=reading_interval,
                )

                if not (run_dir / 'capture.json').is_file():
                    raise click.ClickException(
                        'Record-side run did not produce capture.json; refusing to run the replay side without '
                        'same-fixture replay input.'
                    )

                replay_mode = 'replay'
                replay_fixture = 'capture.json'
                phase = 'replay_run'
                replay_returncode = _run_hatch(
                    repo=replay_tree,
                    platform_repo=StdPath(str(app.repo.path)),
                    artifacts=run_dir,
                    integration=integration.name,
                    hatch_env=replay_hatch_env,
                    check_name=integration.name,
                    check_class=check_class,
                    mode=replay_mode,
                    adapter=adapter,
                    config_name='config.json',
                    fixture_name=replay_fixture,
                    output_name='replay.raw.json',
                    readings=readings,
                    replay_time=replay_time,
                    reading_interval=reading_interval,
                )
            else:
                phase = 'record_environment_setup'
                if _ensure_environment(ctx, integration, storage, record_hatch_env, recreate):
                    started_envs.append(record_hatch_env)
                record_config = storage.get(integration.name, record_hatch_env).read_config()
                (run_dir / 'record.config.json').write_text(json.dumps(record_config, indent=2, sort_keys=True) + '\n')

                phase = 'record_run'
                record_returncode = _run_hatch(
                    repo=record_tree,
                    platform_repo=StdPath(str(app.repo.path)),
                    artifacts=run_dir,
                    integration=integration.name,
                    hatch_env=record_hatch_env,
                    check_name=integration.name,
                    check_class=check_class,
                    mode='record',
                    adapter=adapter,
                    config_name='record.config.json',
                    fixture_name='capture.json',
                    output_name='record.raw.json',
                    readings=readings,
                    replay_time=replay_time,
                    reading_interval=reading_interval,
                )

                if record_hatch_env in started_envs:
                    _stop_environment(ctx, integration, record_hatch_env)
                    started_envs.remove(record_hatch_env)

                phase = 'replay_environment_setup'
                if _ensure_environment(ctx, integration, storage, replay_hatch_env, recreate):
                    started_envs.append(replay_hatch_env)
                replay_config = storage.get(integration.name, replay_hatch_env).read_config()
                (run_dir / 'replay.config.json').write_text(json.dumps(replay_config, indent=2, sort_keys=True) + '\n')

                replay_mode = 'record'
                phase = 'replay_run'
                replay_returncode = _run_hatch(
                    repo=replay_tree,
                    platform_repo=StdPath(str(app.repo.path)),
                    artifacts=run_dir,
                    integration=integration.name,
                    hatch_env=replay_hatch_env,
                    check_name=integration.name,
                    check_class=check_class,
                    mode='record',
                    adapter=adapter,
                    config_name='replay.config.json',
                    fixture_name='replay.capture.json',
                    output_name='replay.raw.json',
                    readings=readings,
                    replay_time=replay_time,
                    reading_interval=reading_interval,
                )

            status = {
                'record_returncode': record_returncode,
                'replay_returncode': replay_returncode,
                'record_mode': record_mode,
                'replay_mode': replay_mode,
                'phase': 'complete',
                'comparison_mode': comparison_mode,
                'same_fixture': same_fixture,
                'replay_cache': replay_cache_provenance,
                'readings': readings,
                'replay_time': replay_time,
                'reading_interval': reading_interval,
                'comparable': record_returncode == 0
                and replay_returncode == 0
                and (replay_mode == 'replay' or not same_fixture),
            }
            (run_dir / 'run_status.json').write_text(json.dumps(status, indent=2, sort_keys=True) + '\n')
    except Exception as e:
        app.display_warning(f'compare-check failed for {integration.name}:{environment} during {phase}: {e}')
        status = {
            'record_returncode': record_returncode,
            'replay_returncode': replay_returncode,
            'record_mode': record_mode,
            'replay_mode': replay_mode,
            'phase': phase,
            'comparison_mode': comparison_mode,
            'same_fixture': same_fixture,
            'replay_cache': replay_cache_provenance,
            'readings': readings,
            'replay_time': replay_time,
            'reading_interval': reading_interval,
            'comparable': False,
            'error': str(e),
            'exception_type': type(e).__name__,
        }
        (run_dir / 'run_status.json').write_text(json.dumps(status, indent=2, sort_keys=True) + '\n')
    finally:
        for env_name in reversed(started_envs):
            try:
                _stop_environment(ctx, integration, env_name)
            except Exception as e:
                app.display_warning(f'Failed to stop environment {integration.name}:{env_name}: {e}')

    _scrub_replay_artifacts(run_dir)

    if refs:
        refs['redaction'] = {'version': 1, 'enabled': True}
        _write_fixture_key(
            run_dir,
            refs,
            integration=integration.name,
            adapter=adapter,
            record_hatch_env=record_hatch_env,
            replay_hatch_env=replay_hatch_env,
            comparison_mode=comparison_mode,
            fixture_env=fixture_env,
            record_head=record_head,
            replay_head=replay_head,
            check_class=check_class,
            readings=readings,
        )
        (run_dir / 'refs.json').write_text(json.dumps(refs, indent=2, sort_keys=True) + '\n')

    return run_dir, _write_diff_artifacts(run_dir)


def _scrub_replay_artifacts(run_dir: StdPath) -> None:
    for name in ('config.json', 'record.config.json', 'replay.config.json'):
        path = run_dir / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text())
        except Exception:
            continue
        path.write_text(json.dumps(scrub_json(data), indent=2, sort_keys=True) + '\n')


def _format_diff_summary(diff: dict) -> str:
    status = diff.get('run_status', {})
    prefix = 'Incomplete; ' if diff.get('incomplete') else ''
    collection_summary = '; '.join(
        f'{name} +{len(diff["collections"].get(name, {}).get("added", []))} '
        f'-{len(diff["collections"].get(name, {}).get("removed", []))}'
        for name in OUTPUT_COLLECTIONS
    )
    return (
        f'{prefix}Changed: {diff["changed"]}; '
        f'record rc {status.get("record_returncode", "?")}; '
        f'replay rc {status.get("replay_returncode", "?")}; '
        f'{collection_summary}'
    )


def _replay_cache_provenance(
    repo_path, integration: str, environment: str, replay_cache: StdPath | None
) -> dict | None:
    if replay_cache is None:
        return None

    cache_dir = replay_cache.resolve()
    default_root = (StdPath(str(repo_path)) / '.ddev' / 'replay' / integration / environment).resolve()
    provenance = {
        'source_run_id': cache_dir.name,
    }
    try:
        relative = cache_dir.relative_to(default_root)
    except ValueError:
        provenance['source'] = 'external'
    else:
        provenance['source'] = 'default-artifact-root'
        provenance['cache_root'] = f'.ddev/replay/{integration}/{environment}'
        provenance['relative_path'] = relative.as_posix()
    return provenance


def _required_cache_files(comparison_mode: str) -> list[str]:
    if comparison_mode == 'same-fixture-replay':
        return ['config.json', 'capture.json']
    return ['record.config.json', 'capture.json', 'replay.config.json', 'replay.capture.json']


def _file_sha256(path: StdPath) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _fixture_bundle_file_names(run_dir: StdPath, manifest_name: str) -> list[str]:
    manifest_path = run_dir / manifest_name
    if not manifest_path.is_file():
        return [manifest_name]

    try:
        manifest = json.loads(manifest_path.read_text())
    except Exception:
        return [manifest_name]

    if not isinstance(manifest, dict):
        return [manifest_name]

    files = [manifest_name]
    component_files = manifest.get('files', {})
    if isinstance(component_files, dict):
        files.extend(str(name) for name in component_files.values())
    return files


def _cache_file_names(run_dir: StdPath, comparison_mode: str) -> list[str]:
    if comparison_mode == 'same-fixture-replay':
        names = ['config.json']
        names.extend(_fixture_bundle_file_names(run_dir, 'capture.json'))
        return names

    names = ['record.config.json']
    names.extend(_fixture_bundle_file_names(run_dir, 'capture.json'))
    names.append('replay.config.json')
    names.extend(_fixture_bundle_file_names(run_dir, 'replay.capture.json'))
    return names


def _write_fixture_key(
    run_dir: StdPath,
    refs: dict,
    *,
    integration: str,
    adapter: str,
    record_hatch_env: str,
    replay_hatch_env: str,
    comparison_mode: str,
    fixture_env: str | None,
    record_head: str,
    replay_head: str,
    check_class: str | None,
    readings: int,
) -> None:
    files = {}
    for name in _cache_file_names(run_dir, comparison_mode):
        path = run_dir / name
        if path.is_file():
            files[name] = _file_sha256(path)

    refs['fixture_key'] = {
        'version': 1,
        'cache_version': REPLAY_CACHE_VERSION,
        'integration': integration,
        'adapter': adapter,
        'comparison_mode': comparison_mode,
        'fixture_env': fixture_env,
        'record_env': record_hatch_env,
        'replay_env': replay_hatch_env,
        'record_head': record_head,
        'replay_head': replay_head if comparison_mode == 'record-each-side' else None,
        'check_class': check_class,
        'readings': readings,
        'files': files,
    }


def _resolve_replay_cache(
    repo_path,
    integration: str,
    environment: str,
    replay_cache: str | None,
    adapter: str,
    record_hatch_env: str,
    replay_hatch_env: str,
    comparison_mode: str,
    *,
    record_head: str,
    replay_head: str,
    check_class: str | None,
    readings: int,
) -> StdPath | None:
    if not replay_cache:
        return None

    if replay_cache not in ('auto', 'latest'):
        cache_dir = StdPath(replay_cache)
        if not cache_dir.is_dir():
            raise click.ClickException(f'Replay cache directory does not exist: {cache_dir}')
        return cache_dir

    cache_root = StdPath(str(repo_path)) / '.ddev' / 'replay' / integration / environment
    candidates = _iter_replay_cache_candidates(cache_root)
    for candidate in candidates:
        if _is_suitable_replay_cache(
            candidate,
            integration=integration,
            adapter=adapter,
            record_hatch_env=record_hatch_env,
            replay_hatch_env=replay_hatch_env,
            comparison_mode=comparison_mode,
            fixture_env=environment if comparison_mode == 'same-fixture-replay' else None,
            record_head=record_head,
            replay_head=replay_head,
            check_class=check_class,
            readings=readings,
        ):
            return candidate

    raise click.ClickException(
        f'Unable to find a suitable replay cache under {cache_root}. '
        'Run compare-check once without --replay-cache to create one, or pass an explicit artifact directory.'
    )


def _iter_replay_cache_candidates(cache_root: StdPath) -> list[StdPath]:
    if not cache_root.is_dir():
        return []

    candidates = []
    latest = cache_root / 'latest'
    if latest.exists():
        try:
            candidates.append(latest.resolve())
        except OSError:
            pass

    latest_txt = cache_root / 'latest.txt'
    if latest_txt.is_file():
        latest_path = StdPath(latest_txt.read_text().strip())
        if latest_path.is_dir():
            candidates.append(latest_path)

    candidates.extend(path for path in cache_root.iterdir() if path.is_dir() and path.name != 'latest')
    unique_candidates = {candidate.resolve(): candidate for candidate in candidates if candidate.is_dir()}
    return sorted(unique_candidates, key=lambda path: path.stat().st_mtime, reverse=True)


def _is_suitable_replay_cache(
    cache_dir: StdPath,
    *,
    integration: str,
    adapter: str,
    record_hatch_env: str,
    replay_hatch_env: str,
    comparison_mode: str,
    fixture_env: str | None,
    record_head: str,
    replay_head: str,
    check_class: str | None,
    readings: int,
) -> bool:
    required_files = _required_cache_files(comparison_mode)
    if any(not (cache_dir / name).is_file() for name in required_files):
        return False

    cache_files = _cache_file_names(cache_dir, comparison_mode)
    if any(not (cache_dir / name).is_file() for name in cache_files):
        return False

    refs_file = cache_dir / 'refs.json'
    if not refs_file.is_file():
        return False

    try:
        refs = json.loads(refs_file.read_text())
    except Exception:
        return False

    fixture_key = refs.get('fixture_key')
    if not isinstance(fixture_key, dict):
        return False

    expected = {
        'version': 1,
        'cache_version': REPLAY_CACHE_VERSION,
        'integration': integration,
        'adapter': adapter,
        'comparison_mode': comparison_mode,
        'fixture_env': fixture_env,
        'record_env': record_hatch_env,
        'replay_env': replay_hatch_env,
        'record_head': record_head,
        'replay_head': replay_head if comparison_mode == 'record-each-side' else None,
        'check_class': check_class,
        'readings': readings,
    }

    if any(fixture_key.get(key) != value for key, value in expected.items()):
        return False

    hashes = fixture_key.get('files')
    if not isinstance(hashes, dict):
        return False

    return all(hashes.get(name) == _file_sha256(cache_dir / name) for name in cache_files)


def _resolve_artifacts_dir(
    repo_path,
    artifacts: StdPath | None,
    integration: str,
    environment: str,
    replay_ref: str,
    exact: bool,
    overwrite: bool,
) -> StdPath:
    root = artifacts or (StdPath(str(repo_path)) / '.ddev' / 'replay')
    if exact:
        run_dir = root
        latest_root = root.parent
    else:
        run_id = f'{datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")}-{_slug(replay_ref)}'
        latest_root = root / integration / environment
        run_dir = latest_root / run_id

    if run_dir.exists():
        if overwrite:
            shutil.rmtree(run_dir)
        else:
            raise click.ClickException(
                f'Artifacts directory already exists: {run_dir}. Use --overwrite or omit --exact-artifacts-dir.'
            )

    run_dir.mkdir(parents=True)
    _update_latest(latest_root, run_dir)
    return run_dir


def _slug(value: str) -> str:
    value = re.sub(r'[^A-Za-z0-9_.-]+', '-', value).strip('-')
    return value[:60] or 'run'


def _update_latest(root: StdPath, run_dir: StdPath) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / 'latest.txt').write_text(str(run_dir) + '\n')
    latest = root / 'latest'
    try:
        if latest.is_symlink() or latest.exists():
            latest.unlink()
        latest.symlink_to(run_dir, target_is_directory=True)
    except OSError:
        # Symlinks are a convenience; latest.txt is the portable pointer.
        pass


def _copy_cache_file(cache_dir: StdPath, run_dir: StdPath, name: str) -> None:
    source = cache_dir / name
    if not source.is_file():
        raise click.ClickException(f'Replay cache is missing required file: {source}')
    shutil.copy2(source, run_dir / name)


def _copy_fixture_bundle(cache_dir: StdPath, run_dir: StdPath, manifest_name: str) -> None:
    _copy_cache_file(cache_dir, run_dir, manifest_name)
    manifest = json.loads((run_dir / manifest_name).read_text())
    if not isinstance(manifest, dict):
        return

    component_files = manifest.get('files', {})
    if not isinstance(component_files, dict):
        raise click.ClickException(f'Replay fixture manifest has invalid files map: {cache_dir / manifest_name}')
    for component_name in component_files.values():
        _copy_cache_file(cache_dir, run_dir, str(component_name))


def _ensure_environment(ctx: click.Context, integration, storage, environment: str, recreate: bool) -> bool:
    from ddev.cli.env.start import start
    from ddev.cli.env.stop import stop

    env_data = storage.get(integration.name, environment)
    if recreate and env_data.exists():
        ctx.invoke(stop, intg_name=integration.name, environment=environment, ignore_state=False)

    if env_data.exists():
        return False

    ctx.invoke(
        start,
        intg_name=integration.name,
        environment=environment,
        local_dev=False,
        local_base=False,
        agent_build=None,
        extra_env_vars=(),
        dogstatsd=False,
        hide_help=True,
        ignore_state=False,
    )
    return True


def _stop_environment(ctx: click.Context, integration, environment: str) -> None:
    from ddev.cli.env.stop import stop

    ctx.invoke(stop, intg_name=integration.name, environment=environment, ignore_state=False)


def _git_worktree(repo, ref: str, path: StdPath) -> None:
    subprocess.run(['git', '-C', str(repo), 'worktree', 'add', '--detach', str(path), ref], check=True)


def _git_rev_parse(repo, ref: str) -> str:
    return subprocess.check_output(['git', '-C', str(repo), 'rev-parse', ref], text=True).strip()


def _git_dirty(repo) -> bool:
    return bool(subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain'], text=True).strip())


def _run_hatch(
    *,
    repo: StdPath,
    platform_repo: StdPath,
    artifacts: StdPath,
    integration: str,
    hatch_env: str,
    check_name: str,
    check_class: str | None,
    mode: str,
    adapter: str,
    config_name: str,
    fixture_name: str,
    output_name: str,
    readings: int,
    replay_time: float,
    reading_interval: float,
) -> int:
    integration_dir = repo / integration
    env = os.environ.copy()
    env['DDEV_SKIP_GENERIC_TAGS_CHECK'] = 'true'
    env.pop('PYTHONPATH', None)
    env.pop('VIRTUAL_ENV', None)

    hatch = [sys.executable, '-m', 'hatch', '--no-color', '--no-interactive', 'run', f'{hatch_env}:python']
    install_result = subprocess.run(
        [*hatch, '-m', 'pip', 'install', '-q', '-e', str(platform_repo / 'datadog_checks_dev')],
        cwd=integration_dir,
        env=env,
        check=False,
    )
    if install_result.returncode != 0:
        return install_result.returncode

    run_args = [
        *hatch,
        '-m',
        'datadog_checks.dev.replay.check_runner',
        '--check-name',
        check_name,
        '--config',
        str(artifacts / config_name),
        '--mode',
        mode,
        '--fixture',
        str(artifacts / fixture_name),
        '--output',
        str(artifacts / output_name),
        '--readings',
        str(readings),
        '--replay-time',
        str(replay_time),
        '--reading-interval',
        str(reading_interval),
        '--adapters',
        adapter,
    ]
    if check_class:
        run_args.extend(('--check-class', check_class))

    result = subprocess.run(run_args, cwd=integration_dir, env=env, check=False)
    return result.returncode


def _reading_outputs(envelope: dict) -> list[dict]:
    if envelope.get('version') == 2 and isinstance(envelope.get('readings'), list):
        return [reading.get('output', {}) for reading in envelope['readings']]
    return [envelope]


def _normalize_reading_envelope(raw: dict) -> dict:
    from datadog_checks.dev.replay.normalize import normalize_output

    if raw.get('version') != 2:
        return normalize_output(raw)
    return {
        'version': 2,
        'readings': [
            {'index': reading.get('index', index), 'output': normalize_output(reading.get('output', {}))}
            for index, reading in enumerate(raw.get('readings', []))
        ],
    }


def _collection_totals(envelope: dict) -> dict[str, int]:
    totals = dict.fromkeys(OUTPUT_COLLECTIONS, 0)
    for output in _reading_outputs(envelope):
        for name in OUTPUT_COLLECTIONS:
            totals[name] += len(output.get(name, []))
    return totals


def _merge_collection_diffs(reading_diffs: list[dict]) -> dict:
    merged: dict[str, dict[str, list]] = {name: {'added': [], 'removed': []} for name in OUTPUT_COLLECTIONS}
    for reading_diff in reading_diffs:
        for name in OUTPUT_COLLECTIONS:
            collection = reading_diff.get('collections', {}).get(name, {})
            merged[name]['added'].extend(collection.get('added', []))
            merged[name]['removed'].extend(collection.get('removed', []))
    return merged


def _diff_reading_envelopes(record_normalized: dict, replay_normalized: dict) -> dict:
    from datadog_checks.dev.replay.diff import diff_outputs

    record_outputs = _reading_outputs(record_normalized)
    replay_outputs = _reading_outputs(replay_normalized)
    reading_diffs = []
    for index, (record_output, replay_output) in enumerate(zip(record_outputs, replay_outputs, strict=False)):
        reading_diff = diff_outputs(record_output, replay_output)
        reading_diff['index'] = index
        reading_diffs.append(reading_diff)

    length_changed = len(record_outputs) != len(replay_outputs)
    return {
        'version': 2,
        'changed': length_changed or any(reading_diff.get('changed') for reading_diff in reading_diffs),
        'reading_count_changed': length_changed,
        'record_readings': len(record_outputs),
        'replay_readings': len(replay_outputs),
        'readings': reading_diffs,
        'collections': _merge_collection_diffs(reading_diffs),
    }


def _write_diff_artifacts(artifacts: StdPath) -> dict:
    status_file = artifacts / 'run_status.json'
    status = json.loads(status_file.read_text()) if status_file.is_file() else {}
    missing = [name for name in ('record.raw.json', 'replay.raw.json') if not (artifacts / name).is_file()]
    if missing:
        diff: dict = {
            'changed': True,
            'incomplete': True,
            'missing_artifacts': missing,
            'run_status': status,
            'collections': {name: {'added': [], 'removed': []} for name in OUTPUT_COLLECTIONS},
        }
        (artifacts / 'diff.json').write_text(json.dumps(diff, indent=2, sort_keys=True) + '\n')
        error = status.get('error')
        error_line = f'- Error: {error}\n' if error else ''
        (artifacts / 'summary.md').write_text(
            '# compare-check summary\n\n'
            '- Incomplete: True\n'
            f'- Missing artifacts: {", ".join(missing)}\n'
            f'- Phase: {status.get("phase", "unknown")}\n'
            f'- Comparison mode: {status.get("comparison_mode", "unknown")}\n'
            f'- Same fixture: {status.get("same_fixture", "unknown")}\n'
            f'- Record return code: {status.get("record_returncode", "unknown")}\n'
            f'- Replay return code: {status.get("replay_returncode", "unknown")}\n'
            f'- Replay mode: {status.get("replay_mode", "unknown")}\n'
            f'{error_line}'
        )
        return diff

    record_raw = scrub_output(json.loads((artifacts / 'record.raw.json').read_text()))
    replay_raw = scrub_output(json.loads((artifacts / 'replay.raw.json').read_text()))
    record_normalized = _normalize_reading_envelope(record_raw)
    replay_normalized = _normalize_reading_envelope(replay_raw)
    diff = _diff_reading_envelopes(record_normalized, replay_normalized)
    diff['run_status'] = status
    diff['incomplete'] = not status.get('comparable', True)
    if diff['incomplete']:
        diff['changed'] = True

    (artifacts / 'record.raw.json').write_text(json.dumps(record_raw, indent=2, sort_keys=True) + '\n')
    (artifacts / 'replay.raw.json').write_text(json.dumps(replay_raw, indent=2, sort_keys=True) + '\n')
    (artifacts / 'record.normalized.json').write_text(json.dumps(record_normalized, indent=2, sort_keys=True) + '\n')
    (artifacts / 'replay.normalized.json').write_text(json.dumps(replay_normalized, indent=2, sort_keys=True) + '\n')
    (artifacts / 'diff.json').write_text(json.dumps(diff, indent=2, sort_keys=True) + '\n')
    record_totals = _collection_totals(record_normalized)
    replay_totals = _collection_totals(replay_normalized)
    collection_lines = ''.join(
        f'- Record {name}: {record_totals[name]}\n'
        f'- Replay {name}: {replay_totals[name]}\n'
        f'- {name} records added: {len(diff["collections"].get(name, {}).get("added", []))}\n'
        f'- {name} records removed: {len(diff["collections"].get(name, {}).get("removed", []))}\n'
        for name in OUTPUT_COLLECTIONS
    )
    (artifacts / 'summary.md').write_text(
        '# compare-check summary\n\n'
        f'- Changed: {diff["changed"]}\n'
        f'- Incomplete: {diff["incomplete"]}\n'
        f'- Comparable: {status.get("comparable", True)}\n'
        f'- Phase: {status.get("phase", "unknown")}\n'
        f'- Comparison mode: {status.get("comparison_mode", "unknown")}\n'
        f'- Same fixture: {status.get("same_fixture", "unknown")}\n'
        f'- Record return code: {status.get("record_returncode", 0)}\n'
        f'- Replay return code: {status.get("replay_returncode", 0)}\n'
        f'{collection_lines}'
    )
    return diff
