# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Behaviour-level tests for the `ddev create` command group."""

from __future__ import annotations

import json

import pytest
import tomli


@pytest.mark.parametrize(
    'subcommand',
    ['check', 'jmx', 'logs', 'event', 'metrics-crawler'],
)
def test_default_manifestless_writes_overrides_and_skips_manifest(ddev, empty_repo, subcommand):
    result = ddev(
        'create',
        subcommand,
        'my_integration',
        '--display-name',
        'My Integration',
        '--metrics-prefix',
        'my_integration.',
        '--platforms',
        'linux,windows,mac_os',
    )
    assert result.exit_code == 0, result.output

    integration_dir = empty_repo.path / 'my_integration'
    assert integration_dir.is_dir()
    assert not (integration_dir / 'manifest.json').exists()

    config_toml = empty_repo.path / '.ddev' / 'config.toml'
    assert config_toml.is_file()
    data = tomli.loads(config_toml.read_text())
    assert data['overrides']['display-name']['my_integration'] == 'My Integration'
    assert data['overrides']['metrics-prefix']['my_integration'] == 'my_integration.'
    assert data['overrides']['manifest']['platforms']['my_integration'] == ['linux', 'windows', 'mac_os']


def test_include_manifest_writes_manifest_and_skips_overrides(ddev, empty_repo):
    result = ddev(
        'create',
        'check',
        'my_integration',
        '--include-manifest',
    )
    assert result.exit_code == 0, result.output

    integration_dir = empty_repo.path / 'my_integration'
    assert (integration_dir / 'manifest.json').exists()

    config_toml = empty_repo.path / '.ddev' / 'config.toml'
    assert not config_toml.exists()


def test_skip_manifest_and_include_manifest_conflict(ddev, empty_repo):
    result = ddev(
        'create',
        'check',
        'my_integration',
        '--skip-manifest',
        '--include-manifest',
    )
    assert result.exit_code != 0
    assert 'mutually exclusive' in result.output


def test_skip_manifest_emits_deprecation_warning(ddev, empty_repo):
    result = ddev(
        'create',
        'check',
        'my_integration',
        '--skip-manifest',
        '--display-name',
        'My Integration',
        '--metrics-prefix',
        'my_integration.',
        '--platforms',
        'linux',
    )
    assert result.exit_code == 0, result.output
    assert '--skip-manifest` is deprecated' in result.output


def test_dropped_type_aborts_with_confluence_link(ddev, empty_repo):
    result = ddev('create', 'foo', '--type', 'tile', '--dry-run')
    assert result.exit_code != 0
    assert '6248108729' in result.output


@pytest.mark.parametrize('dropped', ['tile', 'snmp_tile', 'marketplace'])
def test_all_dropped_types_abort(ddev, empty_repo, dropped):
    result = ddev('create', 'foo', '--type', dropped, '--dry-run')
    assert result.exit_code != 0


def test_type_shim_dispatches_to_subcommand(ddev, empty_repo):
    result = ddev(
        'create',
        'my_integration',
        '--type',
        'check',
        '--display-name',
        'My Integration',
        '--metrics-prefix',
        'my_integration.',
        '--platforms',
        'linux',
        '--dry-run',
    )
    assert result.exit_code == 0, result.output
    assert '--type=check` is deprecated' in result.output
    assert 'Will create' in result.output


def test_missing_required_flags_non_tty_abort(ddev, empty_repo, monkeypatch):
    # CliRunner has no real TTY, so stdin is non-interactive by default.
    result = ddev('create', 'check', 'my_integration')
    assert result.exit_code != 0
    assert '--display-name' in result.output
    assert '--metrics-prefix' in result.output
    assert '--platforms' in result.output


def test_dry_run_does_not_write_anything(ddev, empty_repo):
    result = ddev(
        'create',
        'check',
        'my_integration',
        '--display-name',
        'My Integration',
        '--metrics-prefix',
        'my_integration.',
        '--platforms',
        'linux',
        '--dry-run',
    )
    assert result.exit_code == 0, result.output
    assert not (empty_repo.path / 'my_integration').exists()
    assert not (empty_repo.path / '.ddev' / 'config.toml').exists()


def test_datadog_prefix_rejected(ddev, empty_repo):
    result = ddev(
        'create',
        'check',
        'datadog_thing',
        '--display-name',
        'Datadog Thing',
        '--metrics-prefix',
        'datadog_thing.',
        '--platforms',
        'linux',
    )
    assert result.exit_code != 0
    assert 'cannot start with' in result.output


def test_existing_directory_aborts(ddev, empty_repo):
    (empty_repo.path / 'my_integration').mkdir()
    result = ddev(
        'create',
        'check',
        'my_integration',
        '--display-name',
        'My Integration',
        '--metrics-prefix',
        'my_integration.',
        '--platforms',
        'linux',
    )
    assert result.exit_code != 0
    assert 'already exists' in result.output


def test_overrides_accumulate_across_creates(ddev, empty_repo):
    for name in ('first_integration', 'second_integration'):
        result = ddev(
            'create',
            'check',
            name,
            '--display-name',
            name.title().replace('_', ' '),
            '--metrics-prefix',
            f'{name}.',
            '--platforms',
            'linux',
        )
        assert result.exit_code == 0, result.output

    data = tomli.loads((empty_repo.path / '.ddev' / 'config.toml').read_text())
    assert 'first_integration' in data['overrides']['display-name']
    assert 'second_integration' in data['overrides']['display-name']


def test_invalid_platform_rejected(ddev, empty_repo):
    result = ddev(
        'create',
        'check',
        'my_integration',
        '--display-name',
        'My Integration',
        '--metrics-prefix',
        'my_integration.',
        '--platforms',
        'linux,wonkos',
    )
    assert result.exit_code != 0
    assert 'wonkos' in result.output


def test_help_lists_subcommands(ddev):
    result = ddev('create', '--help')
    assert result.exit_code == 0
    for sub in ('check', 'check-only', 'jmx', 'logs', 'event', 'metrics-crawler'):
        assert sub in result.output


def test_all_values_via_flags_never_prompt(ddev, empty_repo, mocker):
    spy = mocker.patch('click.prompt', side_effect=AssertionError('click.prompt should not be called'))
    result = ddev(
        'create',
        'check',
        'my_integration',
        '--display-name',
        'My Integration',
        '--metrics-prefix',
        'my_integration.',
        '--platforms',
        'linux',
    )
    assert result.exit_code == 0, result.output
    spy.assert_not_called()


def test_check_only_requires_existing_manifest(ddev, empty_repo):
    result = ddev(
        'create',
        'check-only',
        'partner_thing',
        '--display-name',
        'Partner Thing',
        '--metrics-prefix',
        'partner_thing.',
        '--platforms',
        'linux',
    )
    assert result.exit_code != 0
    assert 'manifest.json' in result.output


def test_check_only_with_prefilled_manifest(ddev, empty_repo):
    integration_dir = empty_repo.path / 'partner_thing'
    integration_dir.mkdir()
    (integration_dir / 'manifest.json').write_text(
        json.dumps(
            {
                'author': {
                    'name': 'Partner',
                    'support_email': 'support@partner.com',
                    'homepage': 'https://partner.com',
                    'sales_email': 'sales@partner.com',
                }
            }
        )
    )
    result = ddev(
        'create',
        'check-only',
        'partner_thing',
        '--include-manifest',
    )
    # check-only takes the existing manifest dir as input; --include-manifest is required to keep behaviour.
    assert result.exit_code == 0, result.output
