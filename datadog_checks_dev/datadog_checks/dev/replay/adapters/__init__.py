# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from datadog_checks.dev.replay.adapters.process import (
    install_live_recording_process_state,
    install_replay_process_state,
)
from datadog_checks.dev.replay.adapters.psycopg import install_live_recording_psycopg, install_replay_psycopg
from datadog_checks.dev.replay.adapters.requests import install_live_recording_session_get, install_replay_session_get
from datadog_checks.dev.replay.adapters.subprocess import (
    install_live_recording_get_subprocess_output,
    install_replay_get_subprocess_output,
)
from datadog_checks.dev.replay.adapters.tcp import install_live_recording_tcp_clients, install_replay_tcp_clients

ADAPTERS = ('requests', 'subprocess', 'tcp', 'process', 'psycopg')
MODES = ('record', 'replay')


def install_replay_adapters(
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    fixture_path: Path,
    check_name: str | None = None,
    adapters: tuple[str, ...] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Install all available replay adapters into the current pytest process."""
    if mode == 'record':
        return _install_recording_adapters(monkeypatch, fixture_path, check_name, adapters)
    if mode == 'replay':
        return _install_replay_adapters(monkeypatch, fixture_path, check_name, adapters)
    raise AssertionError('unsupported replay mode')


def _install_recording_adapters(
    monkeypatch: pytest.MonkeyPatch, fixture_path: Path, check_name: str | None, adapters: tuple[str, ...] | None
) -> dict[str, list[dict[str, Any]]]:
    enabled_adapters = set(_enabled_adapters(adapters))
    installed: dict[str, list[dict[str, Any]]] = {}
    for adapter in ADAPTERS:
        if adapter not in enabled_adapters:
            continue
        component_path = component_fixture_path(fixture_path, adapter)
        try:
            installed[adapter] = _install_one(monkeypatch, adapter, 'record', component_path, check_name, strict=False)
        except ModuleNotFoundError:
            continue
        except ImportError:
            continue
        except AssertionError:
            if adapter in {'tcp'}:
                continue
            raise
    return installed


def _install_replay_adapters(
    monkeypatch: pytest.MonkeyPatch, fixture_path: Path, check_name: str | None, adapters: tuple[str, ...] | None
) -> dict[str, list[dict[str, Any]]]:
    manifest = read_fixture_manifest(fixture_path)
    enabled_adapters = set(_enabled_adapters(adapters))
    installed: dict[str, list[dict[str, Any]]] = {}
    for adapter in manifest['adapters']:
        if adapter not in enabled_adapters:
            continue
        if adapter not in ADAPTERS:
            raise AssertionError(f'unsupported replay adapter in fixture manifest: {adapter}')
        component_path = fixture_path.with_name(manifest['files'][adapter])
        installed[adapter] = _install_one(monkeypatch, adapter, 'replay', component_path, check_name, strict=True)
    return installed


def _enabled_adapters(adapters: tuple[str, ...] | None) -> tuple[str, ...]:
    if adapters is None:
        return ADAPTERS

    unknown = sorted(set(adapters) - set(ADAPTERS))
    if unknown:
        raise AssertionError(f'unsupported replay adapter: {", ".join(unknown)}')
    return adapters


def _install_one(
    monkeypatch: pytest.MonkeyPatch,
    adapter: str,
    mode: str,
    fixture_path: Path,
    check_name: str | None,
    *,
    strict: bool,
) -> list[dict[str, Any]]:
    if adapter == 'requests':
        if mode == 'record':
            return install_live_recording_session_get(monkeypatch, fixture_path)
        if mode == 'replay':
            return install_replay_session_get(monkeypatch, fixture_path)
    elif adapter == 'subprocess':
        if mode == 'record':
            return install_live_recording_get_subprocess_output(monkeypatch, fixture_path)
        if mode == 'replay':
            return install_replay_get_subprocess_output(monkeypatch, fixture_path)
    elif adapter == 'tcp':
        if mode == 'record':
            return install_live_recording_tcp_clients(monkeypatch, fixture_path, None, strict=strict)
        if mode == 'replay':
            return install_replay_tcp_clients(monkeypatch, fixture_path, None, strict=strict)
    elif adapter == 'process':
        if mode == 'record':
            return install_live_recording_process_state(monkeypatch, fixture_path, None)
        if mode == 'replay':
            return install_replay_process_state(monkeypatch, fixture_path, None)
    elif adapter == 'psycopg':
        if mode == 'record':
            return install_live_recording_psycopg(monkeypatch, fixture_path)
        if mode == 'replay':
            return install_replay_psycopg(monkeypatch, fixture_path)

    if mode not in MODES:
        raise AssertionError('unsupported replay mode')
    raise AssertionError('unsupported replay adapter')


def component_fixture_path(fixture_path: Path, adapter: str) -> Path:
    return fixture_path.with_name(f'{fixture_path.stem}.{adapter}{fixture_path.suffix}')


def write_fixture_manifest(
    fixture_path: Path, adapter_records: dict[str, list[dict[str, Any]]], readings: int = 1
) -> dict[str, Any]:
    files = {}
    counts = {}
    for adapter in ADAPTERS:
        component_path = component_fixture_path(fixture_path, adapter)
        if not component_path.is_file():
            continue
        records = json.loads(component_path.read_text())
        if not records:
            continue
        files[adapter] = component_path.name
        counts[adapter] = len(records)

    manifest = {
        'version': 2,
        'readings': readings,
        'adapters': list(files),
        'files': files,
        'counts': counts,
    }
    fixture_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    return manifest


def read_fixture_manifest(fixture_path: Path) -> dict[str, Any]:
    manifest = json.loads(fixture_path.read_text())
    if not isinstance(manifest, dict) or manifest.get('version') not in {1, 2}:
        raise AssertionError('Invalid replay fixture manifest')
    if not isinstance(manifest.get('adapters'), list) or not isinstance(manifest.get('files'), dict):
        raise AssertionError('Invalid replay fixture manifest')
    if manifest.get('version') == 1:
        manifest['readings'] = 1
    return manifest
