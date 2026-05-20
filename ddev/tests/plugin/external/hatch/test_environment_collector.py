# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path

import pytest

from ddev.plugin.external.hatch.environment_collector import DatadogChecksEnvironmentCollector


@pytest.mark.parametrize(
    'features, version, local_path, expected',
    [
        (['deps'], '', None, 'datadog-checks-base[deps]'),
        ([], '', None, 'datadog-checks-base[deps]'),
        (['deps', 'http'], '', None, 'datadog-checks-base[deps,http]'),
        (['deps'], '1.2.3', None, 'datadog-checks-base[deps]==1.2.3'),
        (
            ['deps'],
            '',
            Path('/repo/integrations-core/datadog_checks_base'),
            '/repo/integrations-core/datadog_checks_base[deps]',
        ),
        (
            ['deps', 'http'],
            '',
            Path('/repo/integrations-core/datadog_checks_base'),
            '/repo/integrations-core/datadog_checks_base[deps,http]',
        ),
    ],
)
def test_format_base_package(features, version, local_path, expected):
    assert DatadogChecksEnvironmentCollector.format_base_package(features, version=version, local_path=local_path) == (
        expected
    )


def test_base_package_install_command_uses_absolute_path_in_core(tmp_path, monkeypatch):
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
        (True, 'self'),
        (False, 'parent'),
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
