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
    default='requests,subprocess,tcp,process,psycopg,clickhouse-connect',
    show_default=True,
    help='Comma-separated replay adapters to install inside the Agent shim.',
)
@click.option('--artifacts', default=None, help='Artifacts root or exact run directory.')
@click.option('--exact-artifacts-dir', is_flag=True, help='Treat --artifacts as the exact run directory.')
@click.option('--overwrite', is_flag=True, help='Remove existing run directory before writing.')
@click.option('--recreate', '-r', is_flag=True, help='Recreate the integration env before running.')
@click.option('--no-environment', is_flag=True, help='Do not start a dd_environment; use stored env config only.')
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
    adapters: str,
    artifacts: str | None,
    exact_artifacts_dir: bool,
    overwrite: bool,
    recreate: bool,
    no_environment: bool,
    fail_on_diff: bool,
) -> None:
    app: Application = ctx.obj
    repo_path = StdPath(str(app.repo.path))
    sys.path.insert(0, str(repo_path / 'datadog_checks_dev'))

    from datadog_checks.dev.replay.agent.runner import run_compare_agent
    from datadog_checks.dev.replay.agent.diff import write_diffs
    from ddev.e2e.config import EnvDataStorage
    from ddev.cli.env.compare_check import _slug, _update_latest, _ensure_environment, _stop_environment

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
    adapter_tuple = tuple(a.strip() for a in adapters.split(',') if a.strip())

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
