# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from datadog_checks.dev.replay.adapters.process import install_live_recording_process_state, install_replay_process_state
from datadog_checks.dev.replay.adapters.psycopg import install_live_recording_psycopg, install_replay_psycopg
from datadog_checks.dev.replay.adapters.requests import install_live_recording_session_get, install_replay_session_get
from datadog_checks.dev.replay.adapters.subprocess import (
    install_live_recording_get_subprocess_output,
    install_replay_get_subprocess_output,
)
from datadog_checks.dev.replay.adapters.tcp import install_live_recording_tcp_clients, install_replay_tcp_clients

ADAPTERS = ('requests', 'subprocess', 'tcp', 'process', 'psycopg')
MODES = ('record', 'replay')


def install_replay_adapter(
    monkeypatch: pytest.MonkeyPatch, adapter: str, mode: str, fixture_path: Path
) -> list[dict[str, Any]]:
    """Install the selected record/replay adapter into the current pytest process."""
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
            return install_live_recording_tcp_clients(monkeypatch, fixture_path)
        if mode == 'replay':
            return install_replay_tcp_clients(monkeypatch, fixture_path)
    elif adapter == 'process':
        if mode == 'record':
            return install_live_recording_process_state(monkeypatch, fixture_path)
        if mode == 'replay':
            return install_replay_process_state(monkeypatch, fixture_path)
    elif adapter == 'psycopg':
        if mode == 'record':
            return install_live_recording_psycopg(monkeypatch, fixture_path)
        if mode == 'replay':
            return install_replay_psycopg(monkeypatch, fixture_path)

    if mode not in MODES:
        raise AssertionError('unsupported replay mode')
    raise AssertionError('unsupported replay adapter')
