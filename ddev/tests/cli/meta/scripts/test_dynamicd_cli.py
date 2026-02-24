# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from types import SimpleNamespace

import pytest

from ddev.config.command_resolver import EMPTY_OUTPUT, NON_ZERO_EXIT, CommandExecutionError


class _FakeApp:
    def __init__(self, llm_command: str = 'echo secret'):
        self.errors: list[str] = []
        self.config = SimpleNamespace(
            raw_data={'dynamicd': {'llm_api_key_fetch_command': llm_command}},
            org=SimpleNamespace(config={'api_key': 'dd_api'}),
        )

    def display_error(self, message: str):
        self.errors.append(message)

    def abort(self):
        raise RuntimeError('aborted')


def test_get_api_keys_reports_actionable_nonzero_error(monkeypatch):
    from ddev.cli.meta.scripts._dynamicd import cli as dynamicd_cli

    app = _FakeApp(llm_command='echo super-secret')

    def raise_nonzero(command):
        raise CommandExecutionError(command, 23, 'permission denied', reason=NON_ZERO_EXIT)

    monkeypatch.setattr(dynamicd_cli, 'run_command', raise_nonzero)

    with pytest.raises(RuntimeError, match='aborted'):
        dynamicd_cli._get_api_keys(app)

    assert app.errors
    message = app.errors[-1]
    assert 'dynamicd.llm_api_key_fetch_command' in message
    assert 'exit code 23' in message
    assert 'stdout' in message
    assert 'super-secret' not in message


def test_get_api_keys_reports_actionable_empty_output_error(monkeypatch):
    from ddev.cli.meta.scripts._dynamicd import cli as dynamicd_cli

    app = _FakeApp()

    def raise_empty(command):
        raise CommandExecutionError(command, 0, '', reason=EMPTY_OUTPUT)

    monkeypatch.setattr(dynamicd_cli, 'run_command', raise_empty)

    with pytest.raises(RuntimeError, match='aborted'):
        dynamicd_cli._get_api_keys(app)

    message = app.errors[-1]
    assert 'dynamicd.llm_api_key_fetch_command' in message
    assert 'empty output' in message
    assert 'non-empty value' in message
