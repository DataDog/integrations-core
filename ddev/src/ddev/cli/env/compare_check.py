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

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command('compare-check', short_help='Compare no-Agent check output across two refs')
@click.argument('intg_name', metavar='INTEGRATION')
@click.argument('environment', required=False)
@click.option('--old-ref', required=True, help='Git ref to record the fixture and produce old output')
@click.option(
    '--new-ref',
    help='Git ref to replay the fixture and produce new output. Defaults to the current working tree.',
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
@click.option('--adapter', default='requests', show_default=True, type=click.Choice(['requests', 'subprocess']))
@click.option(
    '--old-env',
    'old_hatch_env',
    help='Hatch env for the old side. Defaults to the selected fixture environment.',
)
@click.option(
    '--new-env',
    'new_hatch_env',
    help='Hatch env for the new side. Defaults to the selected fixture environment.',
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
    '--fail-on-diff',
    is_flag=True,
    help='Exit non-zero when any selected environment has a diff or incomplete comparison.',
)
@click.pass_context
def compare_check(
    ctx: click.Context,
    *,
    intg_name: str,
    environment: str | None,
    old_ref: str,
    new_ref: str | None,
    check_class: str | None,
    artifacts: StdPath | None,
    exact_artifacts_dir: bool,
    overwrite: bool,
    replay_cache: str | None,
    adapter: str,
    old_hatch_env: str | None,
    new_hatch_env: str | None,
    comparison_mode: str,
    recreate: bool,
    fail_on_diff: bool,
):
    """
    Compare no-Agent check output across two integrations-core refs.

    This implementation records input from OLD_REF and replays it to NEW_REF through
    isolated Hatch environments.
    """
    from ddev.e2e.config import EnvDataStorage

    app: Application = ctx.obj
    integration = app.repo.integrations.get(intg_name)
    storage = EnvDataStorage(app.data_dir)
    if comparison_mode == 'record-each-side':
        if environment is not None:
            raise click.ClickException('record-each-side mode uses --old-env/--new-env; omit ENVIRONMENT.')
        if not old_hatch_env or not new_hatch_env:
            raise click.ClickException('record-each-side mode requires both --old-env and --new-env.')
        env_names = [f'{old_hatch_env}__vs__{new_hatch_env}']
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
        effective_old_env = old_hatch_env or env_name
        effective_new_env = new_hatch_env or env_name
        old_head = _git_rev_parse(app.repo.path, old_ref)
        new_head = _git_rev_parse(app.repo.path, new_ref or 'HEAD')
        resolved_replay_cache = _resolve_replay_cache(
            app.repo.path,
            integration.name,
            env_name,
            replay_cache,
            adapter,
            effective_old_env,
            effective_new_env,
            comparison_mode,
            old_head=old_head,
            new_head=new_head,
            check_class=check_class,
        )
        if replay_cache_auto:
            app.display_info(f'Using replay cache: {resolved_replay_cache}')

        run_dir, diff = _compare_one_environment(
            ctx=ctx,
            integration=integration,
            environment=env_name,
            storage=storage,
            old_ref=old_ref,
            new_ref=new_ref,
            old_head=old_head,
            new_head=new_head,
            check_class=check_class,
            artifacts=artifacts,
            exact_artifacts_dir=exact_artifacts_dir,
            overwrite=overwrite,
            replay_cache=resolved_replay_cache,
            adapter=adapter,
            old_hatch_env=effective_old_env,
            new_hatch_env=effective_new_env,
            comparison_mode=comparison_mode,
            recreate=recreate,
        )
        batch_results.append((env_name, run_dir, diff))
        app.display_success(f'Wrote compare-check artifacts to {run_dir}')
        app.display_info(_format_diff_summary(diff))

    if len(batch_results) > 1:
        app.display_header('compare-check summary')
        for env_name, run_dir, diff in batch_results:
            app.display_info(f'{env_name}: {_format_diff_summary(diff)} ({run_dir})')

    changed_envs = [env_name for env_name, _, diff in batch_results if diff.get('changed')]
    if fail_on_diff and changed_envs:
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
    old_ref: str,
    new_ref: str | None,
    old_head: str,
    new_head: str,
    check_class: str | None,
    artifacts: StdPath | None,
    exact_artifacts_dir: bool,
    overwrite: bool,
    replay_cache: StdPath | None,
    adapter: str,
    old_hatch_env: str,
    new_hatch_env: str,
    comparison_mode: str,
    recreate: bool,
) -> tuple[StdPath, dict]:
    app: Application = ctx.obj
    run_dir = _resolve_artifacts_dir(
        app.repo.path,
        artifacts,
        integration.name,
        environment,
        new_ref or 'working-tree',
        exact_artifacts_dir,
        overwrite,
    )

    phase = 'artifact_setup'
    started_envs: list[str] = []
    old_returncode = None
    new_returncode = None
    refs: dict = {}
    old_mode = 'replay' if replay_cache else 'record'
    new_mode = None
    same_fixture = comparison_mode == 'same-fixture-replay'
    fixture_env = environment if same_fixture else None
    try:
        new_ref_label = new_ref or 'working-tree'
        refs = {
            'old_ref': old_ref,
            'old_head': old_head,
            'new_ref': new_ref_label,
            'new_head': new_head,
            'new_dirty': _git_dirty(app.repo.path),
            'fixture_env': fixture_env,
            'old_env': old_hatch_env,
            'new_env': new_hatch_env,
            'comparison_mode': comparison_mode,
            'same_fixture': same_fixture,
            'record_ref': 'cache' if replay_cache else 'old',
            'replay_cache': str(replay_cache) if replay_cache else None,
            'adapter': adapter,
            'check_class': check_class,
        }
        (run_dir / 'refs.json').write_text(json.dumps(refs, indent=2, sort_keys=True) + '\n')

        phase = 'worktree_setup'
        with tempfile.TemporaryDirectory(prefix='compare-check-') as temp_dir:
            temp_path = StdPath(temp_dir)
            old_tree = temp_path / 'old'
            _git_worktree(app.repo.path, old_ref, old_tree)
            if new_ref:
                new_tree = temp_path / 'new'
                _git_worktree(app.repo.path, new_ref, new_tree)
            else:
                new_tree = StdPath(str(app.repo.path))

            if replay_cache:
                phase = 'cache_setup'
                if same_fixture:
                    _copy_cache_file(replay_cache, run_dir, 'config.json')
                    _copy_cache_file(replay_cache, run_dir, 'capture.json')

                    phase = 'old_run'
                    old_returncode = _run_hatch(
                        repo=old_tree,
                        platform_repo=StdPath(str(app.repo.path)),
                        artifacts=run_dir,
                        integration=integration.name,
                        hatch_env=old_hatch_env,
                        check_name=integration.name,
                        check_class=check_class,
                        mode='replay',
                        adapter=adapter,
                        config_name='config.json',
                        fixture_name='capture.json',
                        output_name='old.raw.json',
                    )

                    new_mode = 'replay'
                    phase = 'new_run'
                    new_returncode = _run_hatch(
                        repo=new_tree,
                        platform_repo=StdPath(str(app.repo.path)),
                        artifacts=run_dir,
                        integration=integration.name,
                        hatch_env=new_hatch_env,
                        check_name=integration.name,
                        check_class=check_class,
                        mode='replay',
                        adapter=adapter,
                        config_name='config.json',
                        fixture_name='capture.json',
                        output_name='new.raw.json',
                    )
                else:
                    _copy_cache_file(replay_cache, run_dir, 'old.config.json')
                    _copy_cache_file(replay_cache, run_dir, 'capture.json')
                    _copy_cache_file(replay_cache, run_dir, 'new.config.json')
                    _copy_cache_file(replay_cache, run_dir, 'new.capture.json')

                    phase = 'old_run'
                    old_returncode = _run_hatch(
                        repo=old_tree,
                        platform_repo=StdPath(str(app.repo.path)),
                        artifacts=run_dir,
                        integration=integration.name,
                        hatch_env=old_hatch_env,
                        check_name=integration.name,
                        check_class=check_class,
                        mode='replay',
                        adapter=adapter,
                        config_name='old.config.json',
                        fixture_name='capture.json',
                        output_name='old.raw.json',
                    )

                    new_mode = 'replay'
                    phase = 'new_run'
                    new_returncode = _run_hatch(
                        repo=new_tree,
                        platform_repo=StdPath(str(app.repo.path)),
                        artifacts=run_dir,
                        integration=integration.name,
                        hatch_env=new_hatch_env,
                        check_name=integration.name,
                        check_class=check_class,
                        mode='replay',
                        adapter=adapter,
                        config_name='new.config.json',
                        fixture_name='new.capture.json',
                        output_name='new.raw.json',
                    )
            elif same_fixture:
                phase = 'environment_setup'
                if _ensure_environment(ctx, integration, storage, fixture_env, recreate):
                    started_envs.append(fixture_env)

                config = storage.get(integration.name, fixture_env).read_config()
                (run_dir / 'config.json').write_text(json.dumps(config, indent=2, sort_keys=True) + '\n')

                phase = 'old_run'
                old_returncode = _run_hatch(
                    repo=old_tree,
                    platform_repo=StdPath(str(app.repo.path)),
                    artifacts=run_dir,
                    integration=integration.name,
                    hatch_env=old_hatch_env,
                    check_name=integration.name,
                    check_class=check_class,
                    mode='record',
                    adapter=adapter,
                    config_name='config.json',
                    fixture_name='capture.json',
                    output_name='old.raw.json',
                )

                # Prefer replaying the old fixture. If old failed before writing any fixture at all,
                # still run the new side in record mode so both refs get a best-effort execution result.
                new_mode = 'replay' if (run_dir / 'capture.json').is_file() else 'record'
                new_fixture = 'capture.json' if new_mode == 'replay' else 'new.capture.json'
                phase = 'new_run'
                new_returncode = _run_hatch(
                    repo=new_tree,
                    platform_repo=StdPath(str(app.repo.path)),
                    artifacts=run_dir,
                    integration=integration.name,
                    hatch_env=new_hatch_env,
                    check_name=integration.name,
                    check_class=check_class,
                    mode=new_mode,
                    adapter=adapter,
                    config_name='config.json',
                    fixture_name=new_fixture,
                    output_name='new.raw.json',
                )
            else:
                phase = 'old_environment_setup'
                if _ensure_environment(ctx, integration, storage, old_hatch_env, recreate):
                    started_envs.append(old_hatch_env)
                old_config = storage.get(integration.name, old_hatch_env).read_config()
                (run_dir / 'old.config.json').write_text(json.dumps(old_config, indent=2, sort_keys=True) + '\n')

                phase = 'old_run'
                old_returncode = _run_hatch(
                    repo=old_tree,
                    platform_repo=StdPath(str(app.repo.path)),
                    artifacts=run_dir,
                    integration=integration.name,
                    hatch_env=old_hatch_env,
                    check_name=integration.name,
                    check_class=check_class,
                    mode='record',
                    adapter=adapter,
                    config_name='old.config.json',
                    fixture_name='capture.json',
                    output_name='old.raw.json',
                )

                if old_hatch_env in started_envs:
                    _stop_environment(ctx, integration, old_hatch_env)
                    started_envs.remove(old_hatch_env)

                phase = 'new_environment_setup'
                if _ensure_environment(ctx, integration, storage, new_hatch_env, recreate):
                    started_envs.append(new_hatch_env)
                new_config = storage.get(integration.name, new_hatch_env).read_config()
                (run_dir / 'new.config.json').write_text(json.dumps(new_config, indent=2, sort_keys=True) + '\n')

                new_mode = 'record'
                phase = 'new_run'
                new_returncode = _run_hatch(
                    repo=new_tree,
                    platform_repo=StdPath(str(app.repo.path)),
                    artifacts=run_dir,
                    integration=integration.name,
                    hatch_env=new_hatch_env,
                    check_name=integration.name,
                    check_class=check_class,
                    mode='record',
                    adapter=adapter,
                    config_name='new.config.json',
                    fixture_name='new.capture.json',
                    output_name='new.raw.json',
                )

            status = {
                'old_returncode': old_returncode,
                'new_returncode': new_returncode,
                'old_mode': old_mode,
                'new_mode': new_mode,
                'phase': 'complete',
                'comparison_mode': comparison_mode,
                'same_fixture': same_fixture,
                'replay_cache': str(replay_cache) if replay_cache else None,
                'comparable': old_returncode == 0
                and new_returncode == 0
                and (new_mode == 'replay' or not same_fixture),
            }
            (run_dir / 'run_status.json').write_text(json.dumps(status, indent=2, sort_keys=True) + '\n')
    except Exception as e:
        app.display_warning(f'compare-check failed for {integration.name}:{environment} during {phase}: {e}')
        status = {
            'old_returncode': old_returncode,
            'new_returncode': new_returncode,
            'old_mode': old_mode,
            'new_mode': new_mode,
            'phase': phase,
            'comparison_mode': comparison_mode,
            'same_fixture': same_fixture,
            'replay_cache': str(replay_cache) if replay_cache else None,
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

    if refs:
        _write_fixture_key(
            run_dir,
            refs,
            integration=integration.name,
            adapter=adapter,
            old_hatch_env=old_hatch_env,
            new_hatch_env=new_hatch_env,
            comparison_mode=comparison_mode,
            fixture_env=fixture_env,
            old_head=old_head,
            new_head=new_head,
            check_class=check_class,
        )
        (run_dir / 'refs.json').write_text(json.dumps(refs, indent=2, sort_keys=True) + '\n')

    return run_dir, _write_diff_artifacts(run_dir)


def _format_diff_summary(diff: dict) -> str:
    status = diff.get('run_status', {})
    prefix = 'Incomplete; ' if diff.get('incomplete') else ''
    return (
        f'{prefix}Changed: {diff["changed"]}; '
        f'old rc {status.get("old_returncode", "?")}; '
        f'new rc {status.get("new_returncode", "?")}; '
        f'metrics +{len(diff["collections"]["metrics"]["added"])} '
        f'-{len(diff["collections"]["metrics"]["removed"])}'
    )


def _required_cache_files(comparison_mode: str) -> list[str]:
    if comparison_mode == 'same-fixture-replay':
        return ['config.json', 'capture.json']
    return ['old.config.json', 'capture.json', 'new.config.json', 'new.capture.json']


def _file_sha256(path: StdPath) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _write_fixture_key(
    run_dir: StdPath,
    refs: dict,
    *,
    integration: str,
    adapter: str,
    old_hatch_env: str,
    new_hatch_env: str,
    comparison_mode: str,
    fixture_env: str | None,
    old_head: str,
    new_head: str,
    check_class: str | None,
) -> None:
    files = {}
    for name in _required_cache_files(comparison_mode):
        path = run_dir / name
        if path.is_file():
            files[name] = _file_sha256(path)

    refs['fixture_key'] = {
        'version': 1,
        'integration': integration,
        'adapter': adapter,
        'comparison_mode': comparison_mode,
        'fixture_env': fixture_env,
        'old_env': old_hatch_env,
        'new_env': new_hatch_env,
        'record_old_head': old_head,
        'record_new_head': new_head if comparison_mode == 'record-each-side' else None,
        'check_class': check_class,
        'files': files,
    }


def _resolve_replay_cache(
    repo_path,
    integration: str,
    environment: str,
    replay_cache: str | None,
    adapter: str,
    old_hatch_env: str,
    new_hatch_env: str,
    comparison_mode: str,
    *,
    old_head: str,
    new_head: str,
    check_class: str | None,
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
            old_hatch_env=old_hatch_env,
            new_hatch_env=new_hatch_env,
            comparison_mode=comparison_mode,
            fixture_env=environment if comparison_mode == 'same-fixture-replay' else None,
            old_head=old_head,
            new_head=new_head,
            check_class=check_class,
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
    old_hatch_env: str,
    new_hatch_env: str,
    comparison_mode: str,
    fixture_env: str | None,
    old_head: str,
    new_head: str,
    check_class: str | None,
) -> bool:
    required_files = _required_cache_files(comparison_mode)
    if any(not (cache_dir / name).is_file() for name in required_files):
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
        'integration': integration,
        'adapter': adapter,
        'comparison_mode': comparison_mode,
        'fixture_env': fixture_env,
        'old_env': old_hatch_env,
        'new_env': new_hatch_env,
        'record_old_head': old_head,
        'record_new_head': new_head if comparison_mode == 'record-each-side' else None,
        'check_class': check_class,
    }

    if any(fixture_key.get(key) != value for key, value in expected.items()):
        return False

    hashes = fixture_key.get('files')
    if not isinstance(hashes, dict):
        return False

    return all(hashes.get(name) == _file_sha256(cache_dir / name) for name in required_files)


def _resolve_artifacts_dir(
    repo_path,
    artifacts: StdPath | None,
    integration: str,
    environment: str,
    new_ref: str,
    exact: bool,
    overwrite: bool,
) -> StdPath:
    root = artifacts or (StdPath(str(repo_path)) / '.ddev' / 'replay')
    if exact:
        run_dir = root
        latest_root = root.parent
    else:
        run_id = f'{datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")}-{_slug(new_ref)}'
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
        '--adapter',
        adapter,
        '--fixture',
        str(artifacts / fixture_name),
        '--output',
        str(artifacts / output_name),
    ]
    if check_class:
        run_args.extend(('--check-class', check_class))

    result = subprocess.run(run_args, cwd=integration_dir, env=env, check=False)
    return result.returncode


def _write_diff_artifacts(artifacts: StdPath) -> dict:
    from datadog_checks.dev.replay.diff import diff_outputs
    from datadog_checks.dev.replay.normalize import normalize_output

    status_file = artifacts / 'run_status.json'
    status = json.loads(status_file.read_text()) if status_file.is_file() else {}
    missing = [name for name in ('old.raw.json', 'new.raw.json') if not (artifacts / name).is_file()]
    if missing:
        diff = {
            'changed': True,
            'incomplete': True,
            'missing_artifacts': missing,
            'run_status': status,
            'collections': {
                'metrics': {'added': [], 'removed': []},
                'service_checks': {'added': [], 'removed': []},
                'events': {'added': [], 'removed': []},
            },
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
            f'- Old return code: {status.get("old_returncode", "unknown")}\n'
            f'- New return code: {status.get("new_returncode", "unknown")}\n'
            f'- New mode: {status.get("new_mode", "unknown")}\n'
            f'{error_line}'
        )
        return diff

    old_raw = json.loads((artifacts / 'old.raw.json').read_text())
    new_raw = json.loads((artifacts / 'new.raw.json').read_text())
    old_normalized = normalize_output(old_raw)
    new_normalized = normalize_output(new_raw)
    diff = diff_outputs(old_normalized, new_normalized)
    diff['run_status'] = status
    diff['incomplete'] = not status.get('comparable', True)
    if diff['incomplete']:
        diff['changed'] = True

    (artifacts / 'old.normalized.json').write_text(json.dumps(old_normalized, indent=2, sort_keys=True) + '\n')
    (artifacts / 'new.normalized.json').write_text(json.dumps(new_normalized, indent=2, sort_keys=True) + '\n')
    (artifacts / 'diff.json').write_text(json.dumps(diff, indent=2, sort_keys=True) + '\n')
    (artifacts / 'summary.md').write_text(
        '# compare-check summary\n\n'
        f'- Changed: {diff["changed"]}\n'
        f'- Incomplete: {diff["incomplete"]}\n'
        f'- Comparable: {status.get("comparable", True)}\n'
        f'- Phase: {status.get("phase", "unknown")}\n'
        f'- Comparison mode: {status.get("comparison_mode", "unknown")}\n'
        f'- Same fixture: {status.get("same_fixture", "unknown")}\n'
        f'- Old return code: {status.get("old_returncode", 0)}\n'
        f'- New return code: {status.get("new_returncode", 0)}\n'
        f'- Old metrics: {len(old_normalized["metrics"])}\n'
        f'- New metrics: {len(new_normalized["metrics"])}\n'
        f'- Metric records added: {len(diff["collections"]["metrics"]["added"])}\n'
        f'- Metric records removed: {len(diff["collections"]["metrics"]["removed"])}\n'
    )
    return diff
