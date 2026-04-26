# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from functools import cached_property

import pytest

RAW_TARGET_DESCRIPTIONS = [
    {
        'path': 'postgres',
        'is_integration': True,
        'is_package': True,
        'is_tile': False,
        'is_testable': True,
        'is_shippable': True,
        'is_agent_check': True,
        'is_jmx_check': False,
        'has_metrics': True,
    },
    {
        'path': 'kubernetes',
        'is_integration': True,
        'is_package': False,
        'is_tile': True,
        'is_testable': False,
        'is_shippable': False,
        'is_agent_check': False,
        'is_jmx_check': False,
        'has_metrics': True,
    },
    {
        'path': 'ddev',
        'is_integration': False,
        'is_package': True,
        'is_tile': False,
        'is_testable': True,
        'is_shippable': False,
        'is_agent_check': False,
        'is_jmx_check': False,
        'has_metrics': False,
    },
    {
        'path': 'docs',
        'is_integration': False,
        'is_package': False,
        'is_tile': False,
        'is_testable': False,
        'is_shippable': False,
        'is_agent_check': False,
        'is_jmx_check': False,
        'has_metrics': False,
    },
]

TARGET_DESCRIPTIONS = [
    pytest.param(
        RAW_TARGET_DESCRIPTIONS[0],
        id='integration-package',
    ),
    pytest.param(
        RAW_TARGET_DESCRIPTIONS[1],
        id='integration-tile',
    ),
    pytest.param(
        RAW_TARGET_DESCRIPTIONS[2],
        id='package-not-integration',
    ),
    pytest.param(
        RAW_TARGET_DESCRIPTIONS[3],
        id='non-package-not-integration',
    ),
]


def patch_has_metrics(monkeypatch):
    from ddev.integration.core import Integration

    def has_metrics(self):
        if self.name == 'postgres':
            raise OSError('cannot read metadata')

        return (self.path / 'metadata.csv').is_file()

    patched = cached_property(has_metrics)
    patched.__set_name__(Integration, 'has_metrics')
    monkeypatch.setattr(Integration, 'has_metrics', patched)


def test_bool_fields_match_output_model():
    from ddev.cli.meta.catalog import BOOL_FIELDS, TargetDescription

    assert {attr for _, attr in BOOL_FIELDS} == set(TargetDescription.model_fields) - {'path'}


@pytest.mark.parametrize('expected', TARGET_DESCRIPTIONS)
def test_table_output(ddev, repository_as_cwd, expected):
    result = ddev('meta', 'catalog', expected['path'], env={'COLUMNS': '240'})

    assert result.exit_code == 0, result.output
    for header in (
        'Target',
        'Integration',
        'Package',
        'Tile',
        'Testable',
        'Shippable',
        'Agent Check',
        'JMX Check',
        'Metrics',
    ):
        assert header in result.output
    assert expected['path'] in result.output
    assert ('true' if expected['is_integration'] else 'false') in result.output


def test_preserves_target_order(ddev, repository_as_cwd):
    targets = ['docs', 'ddev', 'kubernetes', 'postgres']
    result = ddev('meta', 'catalog', '--format', 'json', *targets)

    assert result.exit_code == 0, result.output
    assert [description['path'] for description in json.loads(result.output)['targets']] == targets


@pytest.mark.parametrize('expected', TARGET_DESCRIPTIONS)
def test_json_output(ddev, repository_as_cwd, expected):
    result = ddev('meta', 'catalog', '--format', 'json', expected['path'])

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {'targets': [expected], 'errors': []}


def test_json_output_with_multiple_targets(ddev, repository_as_cwd):
    targets = [target['path'] for target in RAW_TARGET_DESCRIPTIONS]
    result = ddev('meta', 'catalog', '--format', 'json', *targets)

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {'targets': RAW_TARGET_DESCRIPTIONS, 'errors': []}


def test_json_output_with_absolute_target(ddev, repository_as_cwd):
    result = ddev('meta', 'catalog', '--format', 'json', str(repository_as_cwd.path / 'postgres'))

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {'targets': [RAW_TARGET_DESCRIPTIONS[0]], 'errors': []}


def test_all_targets(ddev, repository_as_cwd):
    result = ddev('meta', 'catalog', '--format', 'json', 'all')

    assert result.exit_code == 0, result.output
    descriptions = json.loads(result.output)['targets']
    descriptions_by_path = {description['path']: description for description in descriptions}
    assert {'postgres', 'kubernetes', 'ddev', 'docs'} <= descriptions_by_path.keys()
    assert descriptions_by_path['ddev']['is_integration'] is False
    assert descriptions_by_path['docs']['is_integration'] is False
    assert json.loads(result.output)['errors'] == []


def test_all_targets_skips_hidden_directories(ddev, repository_as_cwd):
    (repository_as_cwd.path / '.hidden-target').mkdir()

    result = ddev('meta', 'catalog', '--format', 'json', 'all')

    assert result.exit_code == 0, result.output
    assert '.hidden-target' not in {description['path'] for description in json.loads(result.output)['targets']}


def test_all_table_output(ddev, repository_as_cwd):
    result = ddev('meta', 'catalog', 'all', env={'COLUMNS': '240'})

    assert result.exit_code == 0, result.output
    assert 'postgres' in result.output
    assert 'kubernetes' in result.output
    assert 'ddev' in result.output
    assert 'docs' in result.output


def test_all_targets_reports_errors_after_successes(ddev, repository_as_cwd, monkeypatch):
    patch_has_metrics(monkeypatch)

    result = ddev('meta', 'catalog', '--format', 'json', 'all')

    assert result.exit_code == 1, result.output
    catalog = json.loads(result.output)
    assert 'kubernetes' in {description['path'] for description in catalog['targets']}
    assert {'target': 'postgres', 'error': 'cannot read metadata'} in catalog['errors']


def test_all_table_output_reports_errors_after_successes(ddev, repository_as_cwd, monkeypatch):
    patch_has_metrics(monkeypatch)

    result = ddev('meta', 'catalog', 'all', env={'COLUMNS': '240'})

    assert result.exit_code == 1, result.output
    assert 'Targets' in result.output
    assert 'Errors' in result.output
    assert 'kubernetes' in result.output
    assert 'postgres' in result.output
    assert 'cannot read metadata' in result.output


def test_all_cannot_be_combined_with_other_targets(ddev, repository_as_cwd):
    result = ddev('meta', 'catalog', 'all', 'postgres')

    assert result.exit_code == 2, result.output
    assert 'The `all` target cannot be combined with other targets.' in result.output


def test_missing_directory(ddev, repository_as_cwd):
    result = ddev('meta', 'catalog', 'postgres', 'missing', env={'COLUMNS': '240'})

    assert result.exit_code == 1, result.output
    assert 'postgres' in result.output
    assert 'Errors' in result.output
    assert "Directory 'missing' does not exist" in result.output


def test_json_output_with_errors(ddev, repository_as_cwd):
    result = ddev('meta', 'catalog', '--format', 'json', 'postgres', 'missing')

    assert result.exit_code == 1, result.output
    assert json.loads(result.output) == {
        'targets': [RAW_TARGET_DESCRIPTIONS[0]],
        'errors': [{'target': 'missing', 'error': "Directory 'missing' does not exist."}],
    }


def test_json_output_can_be_written_to_file(ddev, repository_as_cwd, tmp_path):
    output_file = tmp_path / 'catalog.json'
    result = ddev('meta', 'catalog', '--format', 'json', '--output', str(output_file), 'postgres')

    assert result.exit_code == 0, result.output
    assert result.output == ''
    assert json.loads(output_file.read_text()) == {'targets': [RAW_TARGET_DESCRIPTIONS[0]], 'errors': []}


def test_output_rejected_for_terminal_format(ddev, repository_as_cwd, tmp_path):
    result = ddev('meta', 'catalog', '--output', str(tmp_path / 'catalog.txt'), 'postgres')

    assert result.exit_code == 2, result.output
    assert '`--output` can only be used with non-terminal formats.' in result.output


def test_no_targets_exits_with_usage_error(ddev, repository_as_cwd):
    result = ddev('meta', 'catalog')

    assert result.exit_code == 2, result.output
    assert 'Missing argument' in result.output
