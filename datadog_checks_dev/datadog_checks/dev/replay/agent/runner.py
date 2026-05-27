# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tier 3 compare-agent runner.

Drives the *real* Datadog Agent binary against a recorded fixture and
captures three probe outputs per Agent run:

- ``freeze.txt``        — ``agent integration freeze`` (IR-53148 oracle).
- ``inventory.json``    — ``agent diagnose show-metadata inventory-checks``.
- ``check.json``        — ``agent check <name> --check-rate --json``.

The fixture is captured during the record run (with the shim in record
mode) and replayed during the replay run (with the shim in replay mode),
mirroring the existing no-Agent ``compare-check`` flow.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from datadog_checks.dev.replay.agent.probes import (
    capture_check_probe,
    capture_freeze_probe,
    capture_inventory_probe,
)
from datadog_checks.dev.replay.agent.shim_builder import build_bundle

DEFAULT_PROBES = ('freeze', 'inventory', 'check')
DEFAULT_ADAPTERS = ('requests', 'subprocess', 'tcp', 'process', 'psycopg', 'clickhouse-connect')

EMBEDDED_PY = '/opt/datadog-agent/embedded/lib/python3.13/site-packages'
AGENT_CMD = '/opt/datadog-agent/bin/agent/agent'


@dataclass
class AgentRunArgs:
    image: str
    role: str  # 'record' or 'replay'
    integration: str
    config: dict[str, Any]
    fixture_dir: Path
    fixture_basename: str  # e.g. 'capture.json'
    mode: str  # 'record' | 'replay'
    artifacts_dir: Path
    probes: tuple[str, ...] = DEFAULT_PROBES
    adapters: tuple[str, ...] = DEFAULT_ADAPTERS
    readings: int = 2
    reading_interval: float = 1.0
    replay_time: float = 1_700_000_000.0
    extra_env: dict[str, str] = field(default_factory=dict)


@dataclass
class AgentRunResult:
    role: str
    image: str
    container_name: str
    probes: dict[str, Path]
    bootstrap_log: Path | None
    agent_version: str | None
    exit_codes: dict[str, int]


def _slugify(value: str) -> str:
    safe = ''.join(ch if ch.isalnum() else '-' for ch in value.lower())
    return safe.strip('-') or 'x'


def _docker(cmd: list[str], *, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, capture_output=capture, text=True)


def _docker_pull_if_missing(image: str) -> None:
    res = subprocess.run(['docker', 'image', 'inspect', image], capture_output=True, text=True)
    if res.returncode == 0:
        return
    subprocess.run(['docker', 'pull', image], check=True)


def run_agent_once(args: AgentRunArgs) -> AgentRunResult:
    """Launch a single Agent container, run the requested probes, return paths."""

    _docker_pull_if_missing(args.image)

    container_name = f'compare-agent-{args.role}-{_slugify(args.integration)}-{uuid.uuid4().hex[:8]}'
    role_dir = args.artifacts_dir / args.role
    role_dir.mkdir(parents=True, exist_ok=True)
    bootstrap_log = role_dir / 'shim_bootstrap.log'

    # Build the shim bundle for this run (re-built each time so live adapter
    # edits propagate).
    shim_root = role_dir / 'shim'
    build_bundle(shim_root)

    # Replay config consumed by ddev_shim.bootstrap inside the container.
    fixture_in_container = f'/shim_fixture/{args.fixture_basename}'
    replay_config = {
        'mode': args.mode,
        'check_name': args.integration,
        'fixture': fixture_in_container,
        'adapters': list(args.adapters),
        'replay_time': args.replay_time,
        'reading_interval': args.reading_interval,
    }
    replay_config_path = role_dir / 'replay_config.json'
    replay_config_path.write_text(json.dumps(replay_config, indent=2, sort_keys=True) + '\n')

    # Build the check config file Agent's `check -C` flag will load.
    conf_dir = role_dir / 'conf'
    conf_dir.mkdir(exist_ok=True)
    conf_yaml_path = conf_dir / f'{args.integration}.yaml'
    import yaml  # local import; available in ddev env
    conf_yaml_path.write_text(yaml.safe_dump(args.config, default_flow_style=False))

    # Marker file the shim reads to advance frozen time between readings.
    # Lives in a writable in-container path mounted from host.
    marker_dir = role_dir / 'marker'
    marker_dir.mkdir(exist_ok=True)
    marker_file = marker_dir / 'reading_index'
    marker_file.write_text('0')

    fixture_dir_abs = args.fixture_dir.resolve()
    fixture_dir_abs.mkdir(parents=True, exist_ok=True)

    docker_env = {
        'DD_API_KEY': '00000000000000000000000000000000',
        'DD_HOSTNAME': 'compare-agent',
        'DD_LOG_LEVEL': 'off',
        'DD_LOG_TO_CONSOLE': 'false',
        'DD_FORWARDER_RETRY_QUEUE_MAX_SIZE': '0',
        'DD_USE_DOGSTATSD': 'false',
        'DD_CLOUD_PROVIDER_METADATA': '[]',
        'DD_INVENTORIES_ENABLED': 'true',
        # Disable subsidiary agents that compete for ports / are irrelevant
        # to the Python check probes we drive.
        'DD_PROCESS_AGENT_ENABLED': 'false',
        'DD_PROCESS_CONFIG_PROCESS_COLLECTION_ENABLED': 'false',
        'DD_SYSTEM_PROBE_ENABLED': 'false',
        'DD_APM_ENABLED': 'false',
        'DD_RUNTIME_SECURITY_CONFIG_ENABLED': 'false',
        'DD_COMPLIANCE_CONFIG_ENABLED': 'false',
        # Each container picks a deterministic port so concurrent runs do
        # not collide on localhost. The ports are container-internal only
        # (we use bridge networking, no port publish), so the value just
        # needs to be free *inside* the container, which it always is.
        'DD_CMD_PORT': '5101',
        'DD_IPC_PORT': '5102',
        'DD_HEALTH_PORT': '0',
        'DD_EXPVAR_PORT': '0',
        'DD_GUI_PORT': '-1',  # disable web GUI entirely
        'DDEV_REPLAY_CONFIG': '/shim/replay_config.json',
        'DDEV_REPLAY_BOOTSTRAP_LOG': '/shim/log/bootstrap.log',
        'DDEV_REPLAY_RUN_MARKER': '/shim/marker/reading_index',
        # Defensive: also include the site-packages root so any embedded3
        # python sub-interpreter spawned by rtloader picks up the shim
        # without relying on sitecustomize alone.
        'PYTHONPATH': '/shim:/opt/datadog-agent/embedded/lib/python3.13/site-packages',
    }
    docker_env.update(args.extra_env)

    log_dir = role_dir / 'docker_log'
    log_dir.mkdir(exist_ok=True)

    # The Agent CLI commands (check, diagnose, integration freeze) speak to
    # the running Agent over IPC and need the auth_token created by the
    # main Agent process at boot. We therefore keep the image's default
    # entrypoint chain and inject the shim via a tiny init script that
    # runs BEFORE the Agent boots: it installs shim files into
    # site-packages, then execs the original entrypoint.
    pre_entry_script = (
        f'set -e; '
        f'cp -r /shim_payload/ddev_shim {EMBEDDED_PY}/ddev_shim 2>/dev/null || true; '
        f'cp /shim_payload/sitecustomize.py {EMBEDDED_PY}/sitecustomize.py 2>/dev/null || true; '
        f'cp /shim_payload/ddev_shim_autoload.pth {EMBEDDED_PY}/ddev_shim_autoload.pth 2>/dev/null || true; '
        f'exec /bin/entrypoint.sh'
    )

    # Bridge networking with port isolation lets us run multiple Agent
    # containers in parallel (record + replay can also coexist with future
    # parallelised dispatcher batches). For integrations whose check needs
    # to reach an upstream service started by `dd_environment`, we add
    # ``--add-host=host.docker.internal:host-gateway`` so the check can
    # reach the host network where the integration env runs.
    cmd = [
        'docker', 'run', '-d', '--rm',
        '--name', container_name,
        '--add-host=host.docker.internal:host-gateway',
        '-v', f'{shim_root}:/shim_payload:ro',
        '-v', f'{replay_config_path}:/shim/replay_config.json:ro',
        '-v', f'{fixture_dir_abs}:/shim_fixture',  # rw so record can write
        '-v', f'{conf_dir}:/shim_conf:ro',
        '-v', f'{marker_dir}:/shim/marker',
        '-v', f'{log_dir}:/shim/log',
    ]
    for key, value in sorted(docker_env.items()):
        cmd.extend(['-e', f'{key}={value}'])
    cmd.extend([
        '--entrypoint', '/bin/sh',
        args.image,
        '-c',
        pre_entry_script,
    ])

    _docker(cmd, capture=False)

    try:
        # Wait for the Agent to come up far enough that the IPC auth_token
        # exists. `agent status` exits 0 once IPC is ready.
        for _ in range(120):
            res = subprocess.run(
                ['docker', 'exec', container_name, AGENT_CMD, 'status', '--json'],
                capture_output=True, timeout=5,
            )
            if res.returncode == 0:
                break
            time.sleep(0.5)

        # Capture Agent version (independent of probes).
        ver_res = subprocess.run(
            ['docker', 'exec', container_name, AGENT_CMD, 'version'],
            capture_output=True, text=True,
        )
        agent_version = ver_res.stdout.strip() if ver_res.returncode == 0 else None

        probes: dict[str, Path] = {}
        exit_codes: dict[str, int] = {}

        if 'freeze' in args.probes:
            out, rc = capture_freeze_probe(container_name, AGENT_CMD)
            probes['freeze'] = role_dir / 'freeze.txt'
            probes['freeze'].write_text(out)
            exit_codes['freeze'] = rc

        if 'inventory' in args.probes:
            out, rc = capture_inventory_probe(container_name, AGENT_CMD)
            probes['inventory'] = role_dir / 'inventory.json'
            probes['inventory'].write_text(out)
            exit_codes['inventory'] = rc

        if 'check' in args.probes:
            out, rc = capture_check_probe(
                container_name=container_name,
                agent_cmd=AGENT_CMD,
                check_name=args.integration,
                conf_path=f'/shim_conf/{args.integration}.yaml',
                readings=args.readings,
                reading_interval=args.reading_interval,
                marker_path_in_container='/shim/marker/reading_index',
            )
            probes['check'] = role_dir / 'check.json'
            probes['check'].write_text(out)
            exit_codes['check'] = rc

        # Pull the bootstrap log out of the container.
        copy_res = subprocess.run(
            ['docker', 'cp', f'{container_name}:/shim/log/bootstrap.log', str(bootstrap_log)],
            capture_output=True, text=True,
        )
        if copy_res.returncode != 0:
            bootstrap_log.write_text('(no bootstrap log produced)\n')
    finally:
        subprocess.run(['docker', 'stop', '-t', '1', container_name], capture_output=True)

    return AgentRunResult(
        role=args.role,
        image=args.image,
        container_name=container_name,
        probes=probes,
        bootstrap_log=bootstrap_log,
        agent_version=agent_version,
        exit_codes=exit_codes,
    )


def run_compare_agent(
    *,
    integration: str,
    environment: str,
    record_image: str,
    replay_image: str,
    config: dict[str, Any],
    artifacts_dir: Path,
    readings: int = 2,
    reading_interval: float = 1.0,
    replay_time: float = 1_700_000_000.0,
    probes: tuple[str, ...] = DEFAULT_PROBES,
    adapters: tuple[str, ...] = DEFAULT_ADAPTERS,
    extra_env: dict[str, str] | None = None,
    cached_fixture_dir: Path | None = None,
) -> dict[str, Any]:
    """End-to-end Agent-vs-Agent comparison.

    Two modes:

    - ``cached_fixture_dir=None``: record + replay in this run. The
      ``record_image`` runs with the shim in record mode, captures HTTP
      / subprocess records into ``artifacts_dir/fixture/``, then the
      ``replay_image`` runs with the shim in replay mode against that
      fixture.

    - ``cached_fixture_dir=<dir>``: reuse a previously seeded fixture.
      Both Agent images run in replay mode against the same fixture.
      This is the preferred mode for the dispatcher because it gives a
      pure behavioural diff without depending on an upstream service.
      The cache is expected to contain ``capture.json`` plus per-adapter
      ``capture.<adapter>.json`` component files (the format written by
      ``compare-check`` or by a previous ``compare-agent`` record run).
    """

    extra_env = extra_env or {}
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    fixture_dir = artifacts_dir / 'fixture'
    fixture_dir.mkdir(exist_ok=True)
    fixture_basename = 'capture.json'

    if cached_fixture_dir is not None:
        _stage_fixture_from_cache(cached_fixture_dir, fixture_dir, fixture_basename)
        record_mode = 'replay'
        skip_record_phase = True
    else:
        record_mode = 'record'
        skip_record_phase = False

    record_args = AgentRunArgs(
        image=record_image,
        role='record',
        integration=integration,
        config=config,
        fixture_dir=fixture_dir,
        fixture_basename=fixture_basename,
        mode=record_mode,
        artifacts_dir=artifacts_dir,
        probes=probes,
        adapters=adapters,
        readings=readings,
        reading_interval=reading_interval,
        replay_time=replay_time,
        extra_env=extra_env,
    )
    record_result = run_agent_once(record_args)

    # After a real record run, assemble a fixture manifest from per-adapter
    # component files the shim wrote into ``fixture_dir``. In cached mode
    # the manifest is already present.
    if not skip_record_phase:
        _assemble_fixture_manifest(fixture_dir / fixture_basename, adapters, readings)

    replay_args = AgentRunArgs(
        image=replay_image,
        role='replay',
        integration=integration,
        config=config,
        fixture_dir=fixture_dir,
        fixture_basename=fixture_basename,
        mode='replay',
        artifacts_dir=artifacts_dir,
        probes=probes,
        adapters=adapters,
        readings=readings,
        reading_interval=reading_interval,
        replay_time=replay_time,
        extra_env=extra_env,
    )
    replay_result = run_agent_once(replay_args)

    summary = {
        'integration': integration,
        'environment': environment,
        'cached_fixture_dir': str(cached_fixture_dir) if cached_fixture_dir else None,
        'fixture_source': 'cache' if cached_fixture_dir else 'live-recorded',
        'record': {
            'image': record_image,
            'agent_version': record_result.agent_version,
            'probes': {k: str(v) for k, v in record_result.probes.items()},
            'exit_codes': record_result.exit_codes,
            'bootstrap_log': str(record_result.bootstrap_log) if record_result.bootstrap_log else None,
        },
        'replay': {
            'image': replay_image,
            'agent_version': replay_result.agent_version,
            'probes': {k: str(v) for k, v in replay_result.probes.items()},
            'exit_codes': replay_result.exit_codes,
            'bootstrap_log': str(replay_result.bootstrap_log) if replay_result.bootstrap_log else None,
        },
        'readings': readings,
        'reading_interval': reading_interval,
        'probes': list(probes),
        'adapters': list(adapters),
    }

    (artifacts_dir / 'run_summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')

    return summary


def _stage_fixture_from_cache(cache_dir: Path, fixture_dir: Path, fixture_basename: str) -> None:
    """Copy a seeded fixture (capture.json + per-adapter files) into the run dir.

    Accepts either:

    - the path of the directory containing ``capture.json`` directly, or
    - a sibling cache layout written by ``compare-check`` where the
      fixture lives at ``<dir>/capture.json`` plus
      ``<dir>/capture.<adapter>.json``.
    """
    import shutil

    cache_dir = cache_dir.resolve()
    if not cache_dir.is_dir():
        raise FileNotFoundError(f'replay cache directory does not exist: {cache_dir}')

    manifest = cache_dir / fixture_basename
    if not manifest.is_file():
        raise FileNotFoundError(
            f'replay cache missing required fixture manifest {fixture_basename} under {cache_dir}'
        )

    fixture_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(manifest, fixture_dir / fixture_basename)

    # Pull every sibling component file matching the manifest stem.
    stem = manifest.stem
    suffix = manifest.suffix or '.json'
    copied = 0
    for src in cache_dir.glob(f'{stem}.*{suffix}'):
        if src.name == manifest.name:
            continue
        shutil.copy2(src, fixture_dir / src.name)
        copied += 1
    if copied == 0:
        raise FileNotFoundError(
            f'replay cache at {cache_dir} contains a manifest but no '
            f'{stem}.<adapter>{suffix} component files'
        )


def _assemble_fixture_manifest(manifest_path: Path, adapters: tuple[str, ...], readings: int) -> None:
    """Build a top-level fixture manifest from per-adapter component files.

    The shim writes per-adapter component files named like
    ``<stem>.<adapter><suffix>`` next to ``<manifest>``. This mirrors the
    no-Agent pytest fixture format so the same replay code consumes them.
    """
    files = {}
    counts = {}
    stem = manifest_path.stem
    suffix = manifest_path.suffix or '.json'
    parent = manifest_path.parent

    for adapter in adapters:
        component = parent / f'{stem}.{adapter}{suffix}'
        if not component.is_file():
            continue
        try:
            records = json.loads(component.read_text())
        except Exception:
            continue
        if not records:
            continue
        files[adapter] = component.name
        counts[adapter] = len(records)

    manifest = {
        'version': 2,
        'readings': readings,
        'adapters': list(files),
        'files': files,
        'counts': counts,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
