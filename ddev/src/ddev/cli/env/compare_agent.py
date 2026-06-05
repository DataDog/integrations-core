# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""``ddev env compare-agent`` — Tier 3 in-Agent shim replay comparison.

Sibling of ``compare-check``. Drives the *real* Datadog Agent binary
against a recorded fixture and surfaces three probe diffs:

- ``freeze.diff.json``     — membership delta (IR-53148 oracle)
- ``inventory.diff.json``  — autodiscovery/loader-error delta
- ``check.diff.json``      — behavioural delta from ``agent check --json``

The command intentionally does **not** accept ``--base`` or any
source-mount option: the unit of comparison is the built Agent
artifact, not a git ref.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path as StdPath
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command('compare-agent', short_help='Compare two Agent images against a shared in-Agent replay fixture')
@click.argument('intg_name', metavar='INTEGRATION')
@click.argument('environment', required=False)
@click.option('--record-image', required=True, help='Agent image used to record the fixture, e.g. datadog/agent:7.78.0')
@click.option('--replay-image', default=None, help='Agent image used to replay against the recorded fixture (defaults to --record-image).')
@click.option('--readings', default=2, show_default=True, help='Number of check readings per Agent invocation.')
@click.option('--reading-interval', default=1.0, show_default=True, help='Frozen-clock interval between readings (seconds).')
@click.option('--replay-time', default=1_700_000_000.0, show_default=True, help='Frozen-clock base time (UNIX seconds).')
@click.option(
    '--probes',
    default='freeze,inventory,check',
    show_default=True,
    help='Comma-separated probes to capture (freeze, inventory, check).',
)
@click.option(
    '--adapters',
    default=None,
    help=(
        'Comma-separated replay adapters to install inside the Agent shim. Defaults to '
        '[tool.datadog.replay].adapters in the integration pyproject.toml; '
        'if that array is missing or empty, replay is unsupported.'
    ),
)
@click.option('--artifacts', default=None, help='Artifacts root or exact run directory.')
@click.option('--exact-artifacts-dir', is_flag=True, help='Treat --artifacts as the exact run directory.')
@click.option('--overwrite', is_flag=True, help='Remove existing run directory before writing.')
@click.option('--recreate', '-r', is_flag=True, help='Recreate the integration env before running.')
@click.option('--no-environment', is_flag=True, help='Do not start a dd_environment; use stored env config only.')
@click.option(
    '--replay-cache',
    default=None,
    help=(
        'Reuse a seeded fixture instead of recording fresh. Pass an explicit cache directory, '
        'or "latest"/"auto" to pick the newest run under '
        '.ddev/replay/<integration>/<environment>/. When set, both Agent images run in replay '
        'mode against the same fixture (no dd_environment startup needed).'
    ),
)
@click.option('--fail-on-diff', is_flag=True, help='Exit non-zero when any probe diff is non-empty.')
@click.pass_context
def compare_agent(
    ctx: click.Context,
    intg_name: str,
    environment: str | None,
    record_image: str,
    replay_image: str | None,
    readings: int,
    reading_interval: float,
    replay_time: float,
    probes: str,
    adapters: str | None,
    artifacts: str | None,
    exact_artifacts_dir: bool,
    overwrite: bool,
    recreate: bool,
    no_environment: bool,
    fail_on_diff: bool,
    replay_cache: str | None,
) -> None:
    app: Application = ctx.obj
    repo_path = StdPath(str(app.repo.path))
    sys.path.insert(0, str(repo_path / 'datadog_checks_dev'))

    from datadog_checks.dev.replay.agent.runner import run_compare_agent
    from datadog_checks.dev.replay.agent.diff import write_diffs
    from ddev.e2e.config import EnvDataStorage
    from ddev.cli.env.compare_check import (
        _ensure_environment,
        _resolve_replay_adapters,
        _slug,
        _stop_environment,
        _update_latest,
    )

    integration = app.repo.integrations.get(intg_name)
    storage = EnvDataStorage(app.repo.path / '.ddev' / 'env' if False else app.data_dir)  # data_dir is the right root

    if environment is None:
        envs = storage.get_environments(integration.name)
        if not envs:
            raise click.ClickException(f'No stored environments for {integration.name}.')
        environment = envs[0]
        click.echo(f'No environment specified; using {environment}')

    started_envs: list[str] = []
    replay_image = replay_image or record_image

    probe_tuple = tuple(p.strip() for p in probes.split(',') if p.strip())
    resolved_adapters = _resolve_replay_adapters(repo_path, integration.name, adapters)
    adapter_tuple = tuple(a.strip() for a in resolved_adapters.split(',') if a.strip())

    cached_fixture_dir = _resolve_replay_cache_for_agent(
        repo_path, integration.name, environment, replay_cache
    ) if replay_cache else None
    # In cache-reuse mode the runner does NOT start a dd_environment because
    # both Agent images replay against the seeded fixture.
    if cached_fixture_dir is not None:
        no_environment = True

    # Resolve artifacts directory.
    root = StdPath(artifacts) if artifacts else (repo_path / '.ddev' / 'replay-agent')
    if exact_artifacts_dir:
        run_dir = root
        latest_root = root.parent
    else:
        run_id = f'{datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")}-{_slug(replay_image)}'
        latest_root = root / integration.name / environment
        run_dir = latest_root / run_id

    if run_dir.exists():
        if overwrite:
            import shutil as _shutil
            _shutil.rmtree(run_dir)
        else:
            raise click.ClickException(
                f'Artifacts directory already exists: {run_dir}. Use --overwrite or omit --exact-artifacts-dir.'
            )

    run_dir.mkdir(parents=True)
    from ddev.utils.fs import Path as DdevPath  # type: ignore
    try:
        _update_latest(DdevPath(str(latest_root)), DdevPath(str(run_dir)))
    except Exception:
        pass

    error_summary: dict | None = None
    try:
        if not no_environment:
            if _ensure_environment(ctx, integration, storage, environment, recreate):
                started_envs.append(environment)

        env_data = storage.get(integration.name, environment)
        config = env_data.read_config()
        if not config:
            if cached_fixture_dir is not None:
                # In cache mode we still need *some* check config so the Agent
                # can load the integration. Fall back to a minimal stub.
                config = {'instances': [{}]}
            else:
                raise click.ClickException(
                    f'No stored config for {integration.name}:{environment}. '
                    f'Run `ddev env start {integration.name} {environment}` first.'
                )

        # Persist the inputs to the run directory for triage.
        (run_dir / 'config.json').write_text(json.dumps(config, indent=2, sort_keys=True) + '\n')
        (run_dir / 'refs.json').write_text(json.dumps({
            'integration': integration.name,
            'environment': environment,
            'record_image': record_image,
            'replay_image': replay_image,
            'readings': readings,
            'reading_interval': reading_interval,
            'replay_time': replay_time,
            'probes': list(probe_tuple),
            'adapters': list(adapter_tuple),
            'tool': 'compare-agent',
            'tool_version': 1,
        }, indent=2, sort_keys=True) + '\n')

        summary = run_compare_agent(
            integration=integration.name,
            environment=environment,
            record_image=record_image,
            replay_image=replay_image,
            config=config,
            artifacts_dir=StdPath(str(run_dir)),
            readings=readings,
            reading_interval=reading_interval,
            replay_time=replay_time,
            probes=probe_tuple,
            adapters=adapter_tuple,
            cached_fixture_dir=cached_fixture_dir,
        )

        diffs = write_diffs(StdPath(str(run_dir)), summary)
    except click.ClickException:
        raise
    except Exception as exc:
        error_summary = {
            'error': str(exc),
            'exception_type': type(exc).__name__,
            'phase': 'run_compare_agent',
        }
        (run_dir / 'run_status.json').write_text(json.dumps(error_summary, indent=2, sort_keys=True) + '\n')
        raise
    finally:
        for env_name in reversed(started_envs):
            try:
                _stop_environment(ctx, integration, env_name)
            except Exception as e:
                app.display_warning(f'Failed to stop {integration.name}:{env_name}: {e}')

    # Write a compact summary.md
    lines: list[str] = []
    lines.append(f'# compare-agent {integration.name}:{environment}')
    lines.append('')
    lines.append(f'- record image: `{record_image}`')
    lines.append(f'- replay image: `{replay_image}`')
    lines.append(f'- readings: {readings}; interval: {reading_interval}s')
    lines.append('')
    nonempty = False
    for probe in ('freeze', 'inventory', 'check'):
        d = diffs.get(probe)
        if d is None:
            lines.append(f'## {probe}: not captured')
            continue
        equal = d.get('equal', False)
        marker = '✅ equal' if equal else '❌ diff'
        lines.append(f'## {probe}: {marker}')
        if not equal:
            nonempty = True
            if probe == 'freeze':
                added = d.get('added') or []
                removed = d.get('removed') or []
                changed = d.get('changed') or []
                if added:
                    lines.append(f'- added: {", ".join(added)}')
                if removed:
                    lines.append(f'- removed: {", ".join(removed)}')
                if changed:
                    lines.append(f'- changed: {len(changed)} package(s)')
            elif probe == 'inventory':
                changed = d.get('changed_check_names', {})
                if changed:
                    lines.append(f'- inventory check-name delta: {json.dumps(changed)}')
            elif probe == 'check':
                m = d.get('metrics', {})
                sc = d.get('service_checks', {})
                lines.append(f'- metrics added/removed: {m.get("added_total", 0)} / {m.get("removed_total", 0)}')
                lines.append(f'- service_checks added/removed: {len(sc.get("added", []))} / {len(sc.get("removed", []))}')
        lines.append('')

    (run_dir / 'summary.md').write_text('\n'.join(lines))
    click.echo(f'compare-agent artifacts at: {run_dir}')
    click.echo(f'summary: {run_dir / "summary.md"}')

    if fail_on_diff and nonempty:
        raise click.ClickException('compare-agent: diff detected (use --fail-on-diff to suppress)')


def _resolve_replay_cache_for_agent(
    repo_path: StdPath,
    integration: str,
    environment: str,
    replay_cache: str,
) -> StdPath | None:
    """Pick a replay-cache directory for the agent runner.

    Honours the same conventions as ``compare-check --replay-cache``:

    - explicit path: used directly after sanity-checks.
    - ``latest``/``auto``: pick the newest run under
      ``.ddev/replay/<integration>/<environment>/`` that contains a
      ``capture.json`` fixture manifest and at least one component file.
    """
    if replay_cache not in ('latest', 'auto'):
        cache_dir = StdPath(replay_cache).resolve()
        if not cache_dir.is_dir():
            raise click.ClickException(f'Replay cache directory does not exist: {cache_dir}')
        return _agent_fixture_root(cache_dir)

    cache_root = repo_path / '.ddev' / 'replay' / integration / environment
    if not cache_root.is_dir():
        raise click.ClickException(
            f'No replay cache root at {cache_root}. '
            f'Run compare-check once to seed a fixture, then retry with --replay-cache latest.'
        )

    # Newest-mtime-first.
    candidates = sorted(
        (p for p in cache_root.iterdir() if p.is_dir()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for candidate in candidates:
        fixture_root = _agent_fixture_root(candidate)
        if fixture_root is not None:
            return fixture_root

    raise click.ClickException(
        f'No usable cache under {cache_root}. '
        f'Expected a child directory containing capture.json + capture.<adapter>.json files.'
    )


def _agent_fixture_root(candidate: StdPath) -> StdPath | None:
    """Return the directory that holds capture.json for an agent run, or None.

    compare-check writes its fixtures at the run-dir root
    (``<run>/capture.json`` etc.). compare-agent in record mode writes
    them under ``<run>/fixture/capture.json``. Detect both layouts.
    """
    if (candidate / 'capture.json').is_file():
        if any(candidate.glob('capture.*.json')):
            return candidate
    nested = candidate / 'fixture'
    if (nested / 'capture.json').is_file():
        if any(nested.glob('capture.*.json')):
            return nested
    return None
