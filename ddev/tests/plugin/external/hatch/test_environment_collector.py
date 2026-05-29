# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import shlex
import sys
from pathlib import Path

import pytest

from ddev.plugin.external.hatch.environment_collector import DatadogChecksEnvironmentCollector, shell_quote


def tokenize(command):
    """Tokenize a generated command the way a POSIX shell does (Hatch runs scripts with ``shell=True``)."""
    return shlex.split(command.replace('{verbosity:flag:-1}', '-q'))


@pytest.mark.parametrize(
    'features, version, local_path, expected',
    [
        pytest.param(['deps'], '', None, 'datadog-checks-base[deps]', id='pypi_with_deps'),
        pytest.param([], '', None, 'datadog-checks-base[deps]', id='pypi_empty_features_defaults_to_deps'),
        pytest.param(['deps', 'http'], '', None, 'datadog-checks-base[deps,http]', id='pypi_multi_features'),
        pytest.param(['deps'], '1.2.3', None, 'datadog-checks-base[deps]==1.2.3', id='pypi_with_version'),
        pytest.param(
            ['deps'],
            '',
            Path('/repo/integrations-core/datadog_checks_base'),
            f"{Path('/repo/integrations-core/datadog_checks_base')}[deps]",
            id='local_path_with_deps',
        ),
        pytest.param(
            ['deps', 'http'],
            '',
            Path('/repo/integrations-core/datadog_checks_base'),
            f"{Path('/repo/integrations-core/datadog_checks_base')}[deps,http]",
            id='local_path_multi_features',
        ),
    ],
)
def test_format_base_package(features, version, local_path, expected):
    assert DatadogChecksEnvironmentCollector.format_base_package(features, version=version, local_path=local_path) == (
        expected
    )


def test_base_package_install_command_uses_absolute_path_in_core(tmp_path, monkeypatch):
    monkeypatch.delenv('DDEV_TEST_BASE_PACKAGE_VERSION', raising=False)

    integrations_core = tmp_path / 'integrations-core'
    (integrations_core / 'datadog_checks_base').mkdir(parents=True)
    integration_root = integrations_core / 'fake_integration'
    integration_root.mkdir()

    monkeypatch.chdir(tmp_path)

    collector = DatadogChecksEnvironmentCollector(integration_root, {})
    command = collector.base_package_install_command(features=None)

    assert command is not None
    assert str(integrations_core / 'datadog_checks_base') in command
    assert '../datadog_checks_base' not in command


def test_test_package_install_command_uses_absolute_path_in_core(tmp_path):
    integrations_core = tmp_path / 'integrations-core'
    (integrations_core / 'datadog_checks_base').mkdir(parents=True)
    (integrations_core / 'datadog_checks_dev').mkdir()
    integration_root = integrations_core / 'fake_integration'
    integration_root.mkdir()

    collector = DatadogChecksEnvironmentCollector(integration_root, {})
    command = collector.test_package_install_command

    assert command is not None
    assert str(integrations_core / 'datadog_checks_dev') in command
    assert '../datadog_checks_dev' not in command


@pytest.mark.parametrize(
    'has_local_ruff_config, expected_relative_to',
    [
        pytest.param(True, 'self', id='local_ruff_config_returns_integration_root'),
        pytest.param(False, 'parent', id='no_local_ruff_config_returns_repo_root'),
    ],
)
def test_ruff_settings_dir_uses_absolute_path(tmp_path, monkeypatch, has_local_ruff_config, expected_relative_to):
    integrations_core = tmp_path / 'integrations-core'
    (integrations_core / 'datadog_checks_base').mkdir(parents=True)
    integration_root = integrations_core / 'fake_integration'
    integration_root.mkdir()

    pyproject = '[project]\nname = "fake"\n'
    if has_local_ruff_config:
        pyproject += '\n[tool.ruff]\nline-length = 120\n'
    (integration_root / 'pyproject.toml').write_text(pyproject)

    monkeypatch.chdir(tmp_path)

    collector = DatadogChecksEnvironmentCollector(integration_root, {})
    settings_dir = collector.ruff_settings_dir()

    expected = str(integration_root) if expected_relative_to == 'self' else str(integrations_core)
    assert settings_dir == expected
    assert settings_dir not in ('.', '..')


def test_format_base_package_quotes_local_path_with_whitespace():
    local_path = Path('/Users/Jane Doe/integrations-core/datadog_checks_base')

    token = DatadogChecksEnvironmentCollector.format_base_package(['deps'], local_path=local_path)
    command = DatadogChecksEnvironmentCollector.uv_install_command('-e', token)

    assert tokenize(command)[-1] == f'{local_path}[deps]'


def test_base_package_install_command_survives_whitespace_checkout(tmp_path, monkeypatch):
    monkeypatch.delenv('DDEV_TEST_BASE_PACKAGE_VERSION', raising=False)

    integrations_core = tmp_path / 'Jane Doe' / 'integrations-core'
    (integrations_core / 'datadog_checks_base').mkdir(parents=True)
    integration_root = integrations_core / 'fake_integration'
    integration_root.mkdir()

    monkeypatch.chdir(tmp_path)

    collector = DatadogChecksEnvironmentCollector(integration_root, {})
    command = collector.base_package_install_command(features=None)

    assert tokenize(command)[-1] == f"{integrations_core / 'datadog_checks_base'}[deps]"


def test_test_package_install_command_survives_whitespace_checkout(tmp_path):
    integrations_core = tmp_path / 'Jane Doe' / 'integrations-core'
    (integrations_core / 'datadog_checks_base').mkdir(parents=True)
    (integrations_core / 'datadog_checks_dev').mkdir()
    integration_root = integrations_core / 'fake_integration'
    integration_root.mkdir()

    collector = DatadogChecksEnvironmentCollector(integration_root, {})
    command = collector.test_package_install_command

    assert tokenize(command)[-1] == str(integrations_core / 'datadog_checks_dev')


@pytest.mark.parametrize(
    'platform, path, expected',
    [
        pytest.param('linux', '/Users/Jane Doe/integrations-core', "'/Users/Jane Doe/integrations-core'", id='linux'),
        pytest.param('darwin', '/Users/Jane Doe/integrations-core', "'/Users/Jane Doe/integrations-core'", id='macos'),
        pytest.param(
            'win32', r'C:\Users\Jane Doe\integrations-core', r'"C:\Users\Jane Doe\integrations-core"', id='win'
        ),
    ],
)
def test_shell_quote_matches_target_shell(monkeypatch, platform, path, expected):
    monkeypatch.setattr(sys, 'platform', platform)

    assert shell_quote(path) == expected


def test_shell_quote_windows_groups_whitespace_path_into_one_token(monkeypatch):
    monkeypatch.setattr(sys, 'platform', 'win32')
    path = r'C:\Users\Jane Doe\integrations-core\datadog_checks_base'

    quoted = shell_quote(path)

    # cmd.exe treats a double-quoted span as a single argument; the path is recovered intact, spaces and all.
    assert quoted == f'"{path}"'
    assert quoted[1:-1] == path


def test_format_base_package_double_quotes_local_path_on_windows(monkeypatch):
    monkeypatch.setattr(sys, 'platform', 'win32')
    local_path = Path('/Users/Jane Doe/integrations-core/datadog_checks_base')

    token = DatadogChecksEnvironmentCollector.format_base_package(['deps'], local_path=local_path)

    assert token == f'"{local_path}"[deps]'


@pytest.mark.parametrize(
    'script_name, config_flag',
    [
        pytest.param('style', '--config', id='ruff_style'),
        pytest.param('fmt', '--config', id='ruff_fmt'),
        pytest.param('typing', '--config-file', id='mypy_typing'),
    ],
)
def test_lint_commands_survive_whitespace_checkout(tmp_path, monkeypatch, script_name, config_flag):
    integrations_core = tmp_path / 'Jane Doe' / 'integrations-core'
    (integrations_core / 'datadog_checks_base').mkdir(parents=True)
    integration_root = integrations_core / 'fake_integration'
    integration_root.mkdir()

    monkeypatch.chdir(tmp_path)

    collector = DatadogChecksEnvironmentCollector(integration_root, {'check-types': True})
    scripts = collector.get_initial_config()['lint']['scripts']

    config_path = str(integrations_core / 'pyproject.toml')
    for command in scripts[script_name]:
        tokens = tokenize(command)
        if config_flag == '--config-file':
            assert f'--config-file={config_path}' in tokens
        else:
            assert config_path == tokens[tokens.index('--config') + 1]
