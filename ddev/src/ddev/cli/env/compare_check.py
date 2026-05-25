# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
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
@click.option('--image', default='datadog/agent-dev:nightly-main-py3', show_default=True)
@click.option('--adapter', default='requests', show_default=True, type=click.Choice(['requests']))
@click.option('--recreate', '-r', is_flag=True, help='Recreate the environment before comparing')
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
    image: str,
    adapter: str,
    recreate: bool,
):
    """
    Compare no-Agent check output across two integrations-core refs.

    This first-slice implementation records HTTP input from OLD_REF and replays the
    same fixture to NEW_REF inside isolated Docker containers.
    """
    from ddev.e2e.config import EnvDataStorage

    app: Application = ctx.obj
    integration = app.repo.integrations.get(intg_name)
    storage = EnvDataStorage(app.data_dir)
    env_names = _select_env_names(ctx, integration, storage, environment)
    if not env_names:
        app.display_info(f"Selected target {integration.name!r} has no matching E2E environments.")
        return

    batch_results = []
    for env_name in env_names:
        app.display_header(f'{integration.display_name}: {env_name}')
        run_dir, diff = _compare_one_environment(
            ctx=ctx,
            integration=integration,
            environment=env_name,
            storage=storage,
            old_ref=old_ref,
            new_ref=new_ref,
            check_class=check_class,
            artifacts=artifacts,
            exact_artifacts_dir=exact_artifacts_dir,
            overwrite=overwrite,
            image=image,
            adapter=adapter,
            recreate=recreate,
        )
        batch_results.append((env_name, run_dir, diff))
        app.display_success(f'Wrote compare-check artifacts to {run_dir}')
        app.display_info(_format_diff_summary(diff))

    if len(batch_results) > 1:
        app.display_header('compare-check summary')
        for env_name, run_dir, diff in batch_results:
            app.display_info(f'{env_name}: {_format_diff_summary(diff)} ({run_dir})')


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
    check_class: str | None,
    artifacts: StdPath | None,
    exact_artifacts_dir: bool,
    overwrite: bool,
    image: str,
    adapter: str,
    recreate: bool,
) -> tuple[StdPath, dict]:
    from ddev.cli.env.start import start
    from ddev.cli.env.stop import stop

    app: Application = ctx.obj
    env_data = storage.get(integration.name, environment)
    started_env = False
    if recreate and env_data.exists():
        ctx.invoke(stop, intg_name=integration.name, environment=environment, ignore_state=False)

    if not env_data.exists():
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
        started_env = True

    run_dir = _resolve_artifacts_dir(
        app.repo.path,
        artifacts,
        integration.name,
        environment,
        new_ref or 'working-tree',
        exact_artifacts_dir,
        overwrite,
    )
    config = env_data.read_config()
    (run_dir / 'config.json').write_text(json.dumps(config, indent=2, sort_keys=True) + '\n')

    try:
        with tempfile.TemporaryDirectory(prefix='compare-check-') as temp_dir:
            temp_path = StdPath(temp_dir)
            old_tree = temp_path / 'old'
            _git_worktree(app.repo.path, old_ref, old_tree)
            if new_ref:
                new_tree = temp_path / 'new'
                _git_worktree(app.repo.path, new_ref, new_tree)
                new_ref_label = new_ref
            else:
                new_tree = StdPath(str(app.repo.path))
                new_ref_label = 'working-tree'

            refs = {
                'old_ref': old_ref,
                'new_ref': new_ref_label,
                'new_head': _git_rev_parse(app.repo.path, 'HEAD'),
                'new_dirty': _git_dirty(app.repo.path),
                'record_ref': 'old',
                'adapter': adapter,
            }
            (run_dir / 'refs.json').write_text(json.dumps(refs, indent=2, sort_keys=True) + '\n')

            old_returncode = _run_container(
                repo=old_tree,
                platform_repo=StdPath(str(app.repo.path)),
                artifacts=run_dir,
                image=image,
                integration=integration.name,
                check_name=integration.name,
                check_class=check_class,
                mode='record',
                fixture_name='capture.json',
                output_name='old.raw.json',
            )

            # Prefer replaying the old fixture. If old failed before writing any fixture at all,
            # still run the new side in record mode so both refs get a best-effort execution result.
            new_mode = 'replay' if (run_dir / 'capture.json').is_file() else 'record'
            new_fixture = 'capture.json' if new_mode == 'replay' else 'new.capture.json'
            new_returncode = _run_container(
                repo=new_tree,
                platform_repo=StdPath(str(app.repo.path)),
                artifacts=run_dir,
                image=image,
                integration=integration.name,
                check_name=integration.name,
                check_class=check_class,
                mode=new_mode,
                fixture_name=new_fixture,
                output_name='new.raw.json',
            )
            status = {
                'old_returncode': old_returncode,
                'new_returncode': new_returncode,
                'new_mode': new_mode,
                'comparable': old_returncode == 0 and new_returncode == 0 and new_mode == 'replay',
            }
            (run_dir / 'run_status.json').write_text(json.dumps(status, indent=2, sort_keys=True) + '\n')
    finally:
        if started_env:
            try:
                ctx.invoke(stop, intg_name=integration.name, environment=environment, ignore_state=False)
            except Exception as e:
                app.display_warning(f'Failed to stop environment {integration.name}:{environment}: {e}')

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


def _git_worktree(repo, ref: str, path: StdPath) -> None:
    subprocess.run(['git', '-C', str(repo), 'worktree', 'add', '--detach', str(path), ref], check=True)


def _git_rev_parse(repo, ref: str) -> str:
    return subprocess.check_output(['git', '-C', str(repo), 'rev-parse', ref], text=True).strip()


def _git_dirty(repo) -> bool:
    return bool(subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain'], text=True).strip())


def _run_container(
    *,
    repo: StdPath,
    platform_repo: StdPath,
    artifacts: StdPath,
    image: str,
    integration: str,
    check_name: str,
    check_class: str | None,
    mode: str,
    fixture_name: str,
    output_name: str,
) -> int:
    python = '/opt/datadog-agent/embedded/bin/python'
    install = ' && '.join(
        [
            f'{python} -m pip install -q -e /platform/datadog_checks_dev',
            f'{python} -m pip install -q -e {shlex.quote("/repo/datadog_checks_base[db,deps,http,json,kube]")}',
            f'{python} -m pip install -q -e {shlex.quote(f"/repo/{integration}[deps]")}',
        ]
    )
    run_args = [
        python,
        '-m datadog_checks.dev.replay.check_runner',
        '--check-name',
        shlex.quote(check_name),
        '--config /artifacts/config.json',
        '--mode',
        mode,
        f'--fixture /artifacts/{fixture_name}',
        '--output',
        f'/artifacts/{output_name}',
    ]
    if check_class:
        run_args.extend(('--check-class', shlex.quote(check_class)))
    run = ' '.join(run_args)
    command = f'{install} && {run}'
    result = subprocess.run(
        [
            'docker',
            'run',
            '--rm',
            '--network',
            'host',
            '-v',
            f'{repo}:/repo:ro',
            '-v',
            f'{platform_repo}:/platform:ro',
            '-v',
            f'{artifacts}:/artifacts',
            '-e',
            'DDEV_SKIP_GENERIC_TAGS_CHECK=true',
            '--entrypoint',
            'bash',
            image,
            '-lc',
            command,
        ],
        check=False,
    )
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
        (artifacts / 'summary.md').write_text(
            '# compare-check summary\n\n'
            '- Incomplete: True\n'
            f'- Missing artifacts: {", ".join(missing)}\n'
            f'- Old return code: {status.get("old_returncode", "unknown")}\n'
            f'- New return code: {status.get("new_returncode", "unknown")}\n'
            f'- New mode: {status.get("new_mode", "unknown")}\n'
        )
        return diff

    old_raw = json.loads((artifacts / 'old.raw.json').read_text())
    new_raw = json.loads((artifacts / 'new.raw.json').read_text())
    old_normalized = normalize_output(old_raw)
    new_normalized = normalize_output(new_raw)
    diff = diff_outputs(old_normalized, new_normalized)
    diff['run_status'] = status

    (artifacts / 'old.normalized.json').write_text(json.dumps(old_normalized, indent=2, sort_keys=True) + '\n')
    (artifacts / 'new.normalized.json').write_text(json.dumps(new_normalized, indent=2, sort_keys=True) + '\n')
    (artifacts / 'diff.json').write_text(json.dumps(diff, indent=2, sort_keys=True) + '\n')
    (artifacts / 'summary.md').write_text(
        '# compare-check summary\n\n'
        f'- Changed: {diff["changed"]}\n'
        f'- Comparable: {status.get("comparable", True)}\n'
        f'- Old return code: {status.get("old_returncode", 0)}\n'
        f'- New return code: {status.get("new_returncode", 0)}\n'
        f'- Old metrics: {len(old_normalized["metrics"])}\n'
        f'- New metrics: {len(new_normalized["metrics"])}\n'
        f'- Metric records added: {len(diff["collections"]["metrics"]["added"])}\n'
        f'- Metric records removed: {len(diff["collections"]["metrics"]["removed"])}\n'
    )
    return diff
