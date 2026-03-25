# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import pytest

from ddev.config.model import RootConfig


class _FakeApp:
    def __init__(self, config: RootConfig):
        self.errors: list[str] = []
        self.config = config

    def display_error(self, message: str):
        self.errors.append(message)

    def abort(self):
        raise RuntimeError('aborted')


def _make_config(dynamicd: dict) -> RootConfig:
    return RootConfig({'dynamicd': dynamicd, 'orgs': {'default': {'api_key': 'dd_api'}}})


def test_get_api_keys_reports_actionable_nonzero_error():
    from ddev.cli.meta.scripts._dynamicd import cli as dynamicd_cli

    app = _FakeApp(_make_config({'llm_api_key_fetch_command': 'echo super-secret >/dev/null && exit 23'}))

    with pytest.raises(RuntimeError, match='aborted'):
        dynamicd_cli._get_api_keys(app)

    assert app.errors
    message = app.errors[-1]
    assert 'dynamicd.llm_api_key_fetch_command' in message
    assert 'exit code 23' in message
    assert 'stdout' in message
    assert 'super-secret' not in message


def test_get_api_keys_reports_actionable_empty_output_error():
    from ddev.cli.meta.scripts._dynamicd import cli as dynamicd_cli

    app = _FakeApp(_make_config({'llm_api_key_fetch_command': 'echo ""'}))

    with pytest.raises(RuntimeError, match='aborted'):
        dynamicd_cli._get_api_keys(app)

    message = app.errors[-1]
    assert 'dynamicd.llm_api_key_fetch_command' in message
    assert 'empty output' in message
    assert 'non-empty value' in message


def test_get_api_keys_plain_value_fallback():
    from ddev.cli.meta.scripts._dynamicd import cli as dynamicd_cli

    app = _FakeApp(_make_config({'llm_api_key': 'plain-key'}))

    llm_api_key, dd_api_key = dynamicd_cli._get_api_keys(app)

    assert llm_api_key == 'plain-key'
    assert dd_api_key == 'dd_api'


def test_get_api_keys_env_fallback(monkeypatch):
    from ddev.cli.meta.scripts._dynamicd import cli as dynamicd_cli

    monkeypatch.setenv('ANTHROPIC_API_KEY', 'env-key')
    app = _FakeApp(_make_config({}))

    llm_api_key, dd_api_key = dynamicd_cli._get_api_keys(app)

    assert llm_api_key == 'env-key'
    assert dd_api_key == 'dd_api'
