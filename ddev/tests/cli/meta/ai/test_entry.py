# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the `ddev meta ai` entry point (TOGOTUI-10)."""

from __future__ import annotations

import logging

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def no_anthropic_env(monkeypatch):
    """Keep the developer's real keys out of tests so the no-key path is reachable."""
    monkeypatch.delenv('DD_ANTHROPIC_API_KEY', raising=False)
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)


@pytest.fixture
def with_api_key(config_file):
    """Set an Anthropic key in config so validation gets past the key check."""
    config_file.model.ai.anthropic_api_key = 'sk-test'
    config_file.save()
    return config_file


# ---------------------------------------------------------------------------
# Help / registration
# ---------------------------------------------------------------------------


def test_ai_help_resolves(ddev):
    result = ddev('meta', 'ai', '--help')

    assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# No-subcommand path: TogoApp construction
# ---------------------------------------------------------------------------


def test_no_subcommand_builds_shared_configuration_components(ddev, mocker, with_api_key):
    """The composition root injects one engine and the same registries into the TUI."""
    from ddev.cli.meta.ai.tui.app import TogoApp

    run_mock = mocker.patch.object(TogoApp, 'run', return_value=None)
    spy = mocker.spy(TogoApp, '__init__')
    engine = mocker.patch('ddev.ai.config.engine.ConfigurationEngine')

    result = ddev('meta', 'ai')

    assert result.exit_code == 0, result.output
    assert run_mock.called
    spy.assert_called_once()
    kwargs = spy.call_args.kwargs
    assert kwargs['engine'] is engine.return_value
    assert kwargs['phase_registry'] is not None
    assert kwargs['provider_registry'] is not None


def test_no_subcommand_passes_ddev_app(ddev, mocker, with_api_key):
    """Invoking the ai group with no subcommand passes the ddev Application as ddev_app."""
    from ddev.cli.meta.ai.tui.app import TogoApp

    mocker.patch.object(TogoApp, 'run', return_value=None)
    spy = mocker.spy(TogoApp, '__init__')

    result = ddev('meta', 'ai')

    assert result.exit_code == 0, result.output
    spy.assert_called_once()
    kwargs = spy.call_args.kwargs
    assert 'ddev_app' in kwargs
    assert kwargs['ddev_app'] is not None


def test_no_subcommand_suppresses_httpx_info_logs_while_togo_runs(ddev, mocker, with_api_key):
    """HTTP request logs do not write over the Textual display."""
    from ddev.cli.meta.ai.tui.app import TogoApp

    httpx_logger = logging.getLogger('httpx')
    previous_level = httpx_logger.level
    observed_levels = []

    def observe_level() -> None:
        observed_levels.append(httpx_logger.level)

    try:
        httpx_logger.setLevel(logging.INFO)
        mocker.patch.object(TogoApp, 'run', side_effect=observe_level)

        result = ddev('meta', 'ai')

        assert result.exit_code == 0, result.output
        assert observed_levels == [logging.WARNING]
        assert httpx_logger.level == logging.INFO
    finally:
        httpx_logger.setLevel(previous_level)


def test_no_subcommand_no_api_key_opens_dashboard(ddev, mocker):
    """Browsing flows does not require provider credentials up front."""
    from ddev.cli.meta.ai.tui.app import TogoApp

    mocker.patch('ddev.ai.config.engine.ConfigurationEngine')
    run_mock = mocker.patch.object(TogoApp, 'run', return_value=None)

    result = ddev('meta', 'ai', catch_exceptions=True)

    assert result.exit_code == 0, result.output
    run_mock.assert_called_once()


def test_no_subcommand_reports_configuration_error(ddev, mocker):
    mocker.patch(
        'ddev.ai.config.engine.ConfigurationEngine',
        side_effect=__import__('ddev.ai.config.errors', fromlist=['ConfigError']).ConfigError('bad flow directory'),
    )

    result = ddev('meta', 'ai', catch_exceptions=True)

    assert result.exit_code == 1
    assert 'bad flow directory' in result.output


def test_no_subcommand_construction_error(ddev, mocker, with_api_key):
    """`ddev meta ai` surfaces an unexpected error when TogoApp.__init__ raises."""
    from ddev.cli.meta.ai.tui.app import TogoApp

    mocker.patch.object(TogoApp, '__init__', side_effect=RuntimeError('construction failed'))

    result = ddev('meta', 'ai', catch_exceptions=True)

    assert result.exit_code != 0
