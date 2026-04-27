# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from functools import cached_property
from pathlib import Path as FilePath

import pytest

from tests.helpers.git import ClonedRepo
from tests.helpers.runner import CliRunner

RAW_TARGET_DESCRIPTIONS = [
    {
        'name': 'postgres',
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
        'name': 'kubernetes',
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
        'name': 'ddev',
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
        'name': 'docs',
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


def patch_has_metrics(monkeypatch: pytest.MonkeyPatch, error: Exception) -> None:
    from ddev.integration.core import Integration

    def has_metrics(self: Integration) -> bool:
        if self.name == 'postgres':
            raise error

        return (self.path / 'metadata.csv').is_file()

    patched = cached_property(has_metrics)
    patched.__set_name__(Integration, 'has_metrics')
    monkeypatch.setattr(Integration, 'has_metrics', patched)


@pytest.fixture
def patched_has_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_has_metrics(monkeypatch, OSError('cannot read metadata'))


@pytest.fixture
def patched_has_metrics_unicode_error(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_has_metrics(monkeypatch, UnicodeDecodeError('utf-8', b'\x80', 0, 1, 'invalid start byte'))


def test_bool_fields_match_output_model() -> None:
    from ddev.cli.meta.catalog import BOOL_FIELDS, TargetDescription

    assert {attr for _, attr in BOOL_FIELDS} == set(TargetDescription.model_fields) - {'name'}


@pytest.mark.parametrize('expected', TARGET_DESCRIPTIONS)
def test_table_output(ddev: CliRunner, repository_as_cwd: ClonedRepo, expected: dict[str, bool | str]) -> None:
    from ddev.cli.meta.catalog import BOOL_FIELDS

    result = ddev('meta', 'catalog', expected['name'], env={'COLUMNS': '240'})

    assert result.exit_code == 0, result.output
    assert 'Target' in result.output
    assert expected['name'] in result.output
    for header, attr in BOOL_FIELDS:
        assert header in result.output
        assert ('true' if expected[attr] else 'false') in result.output


def test_preserves_target_order(ddev: CliRunner, repository_as_cwd: ClonedRepo) -> None:
    targets = ['docs', 'ddev', 'kubernetes', 'postgres']
    result = ddev('meta', 'catalog', '--format', 'json', *targets)

    assert result.exit_code == 0, result.output
    assert [description['name'] for description in json.loads(result.output)['targets']] == targets


@pytest.mark.parametrize('expected', TARGET_DESCRIPTIONS)
def test_json_output(ddev: CliRunner, repository_as_cwd: ClonedRepo, expected: dict[str, bool | str]) -> None:
    result = ddev('meta', 'catalog', '--format', 'json', expected['name'])

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {'targets': [expected], 'errors': []}


def test_json_output_with_multiple_targets(ddev: CliRunner, repository_as_cwd: ClonedRepo) -> None:
    targets = [target['name'] for target in RAW_TARGET_DESCRIPTIONS]
    result = ddev('meta', 'catalog', '--format', 'json', *targets)

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {'targets': RAW_TARGET_DESCRIPTIONS, 'errors': []}


def test_json_output_with_absolute_target(ddev: CliRunner, repository_as_cwd: ClonedRepo) -> None:
    result = ddev('meta', 'catalog', '--format', 'json', str(repository_as_cwd.path / 'postgres'))

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {'targets': [RAW_TARGET_DESCRIPTIONS[0]], 'errors': []}


def test_all_targets(ddev: CliRunner, repository_as_cwd: ClonedRepo) -> None:
    result = ddev('meta', 'catalog', '--format', 'json', 'all')

    assert result.exit_code == 0, result.output
    descriptions = json.loads(result.output)['targets']
    descriptions_by_name = {description['name']: description for description in descriptions}
    assert {'postgres', 'kubernetes', 'ddev', 'docs'} <= descriptions_by_name.keys()
    assert descriptions_by_name['ddev']['is_integration'] is False
    assert descriptions_by_name['docs']['is_integration'] is False
    assert json.loads(result.output)['errors'] == []


def test_all_targets_skips_hidden_directories(ddev: CliRunner, repository_as_cwd: ClonedRepo) -> None:
    (repository_as_cwd.path / '.hidden-target').mkdir()

    result = ddev('meta', 'catalog', '--format', 'json', 'all')

    assert result.exit_code == 0, result.output
    assert '.hidden-target' not in {description['name'] for description in json.loads(result.output)['targets']}


def test_all_table_output(ddev: CliRunner, repository_as_cwd: ClonedRepo) -> None:
    result = ddev('meta', 'catalog', 'all', env={'COLUMNS': '240'})

    assert result.exit_code == 0, result.output
    assert 'postgres' in result.output
    assert 'kubernetes' in result.output
    assert 'ddev' in result.output
    assert 'docs' in result.output


def test_all_targets_reports_errors_after_successes(
    ddev: CliRunner, repository_as_cwd: ClonedRepo, patched_has_metrics: None
) -> None:
    result = ddev('meta', 'catalog', '--format', 'json', 'all')

    assert result.exit_code == 1, result.output
    catalog = json.loads(result.output)
    assert 'kubernetes' in {description['name'] for description in catalog['targets']}
    assert {'target': 'postgres', 'error': 'cannot read metadata'} in catalog['errors']


def test_all_table_output_reports_errors_after_successes(
    ddev: CliRunner, repository_as_cwd: ClonedRepo, patched_has_metrics: None
) -> None:
    result = ddev('meta', 'catalog', 'all', env={'COLUMNS': '240'})

    assert result.exit_code == 1, result.output
    assert 'Targets' in result.output
    assert 'Errors' in result.output
    assert 'kubernetes' in result.output
    assert 'postgres' in result.output
    assert 'cannot read metadata' in result.output


def test_explicit_targets_report_non_os_errors_after_successes(
    ddev: CliRunner, repository_as_cwd: ClonedRepo, patched_has_metrics_unicode_error: None
) -> None:
    result = ddev('meta', 'catalog', '--format', 'json', 'postgres', 'kubernetes')

    assert result.exit_code == 1, result.output
    catalog = json.loads(result.output)
    assert [description['name'] for description in catalog['targets']] == ['kubernetes']
    assert catalog['errors'][0]['target'] == 'postgres'
    assert "can't decode byte" in catalog['errors'][0]['error']


def test_all_cannot_be_combined_with_other_targets(ddev: CliRunner, repository_as_cwd: ClonedRepo) -> None:
    result = ddev('meta', 'catalog', 'all', 'postgres')

    assert result.exit_code == 2, result.output
    assert 'The `all` target cannot be combined with other targets.' in result.output


def test_missing_directory(ddev: CliRunner, repository_as_cwd: ClonedRepo) -> None:
    result = ddev('meta', 'catalog', 'postgres', 'missing', env={'COLUMNS': '240'})

    assert result.exit_code == 1, result.output
    assert 'postgres' in result.output
    assert 'Errors' in result.output
    assert "Target 'missing' is not a directory or does not exist." in result.output


def test_file_target_reports_directory_error(ddev: CliRunner, repository_as_cwd: ClonedRepo) -> None:
    result = ddev('meta', 'catalog', 'postgres', 'pyproject.toml', env={'COLUMNS': '240'})

    assert result.exit_code == 1, result.output
    assert 'postgres' in result.output
    assert 'Errors' in result.output
    assert "Target 'pyproject.toml' is not a directory or does not exist." in result.output


def test_json_output_with_errors(ddev: CliRunner, repository_as_cwd: ClonedRepo) -> None:
    result = ddev('meta', 'catalog', '--format', 'json', 'postgres', 'missing')

    assert result.exit_code == 1, result.output
    assert json.loads(result.output) == {
        'targets': [RAW_TARGET_DESCRIPTIONS[0]],
        'errors': [{'target': 'missing', 'error': "Target 'missing' is not a directory or does not exist."}],
    }


def test_json_output_can_be_written_to_file(ddev: CliRunner, repository_as_cwd: ClonedRepo, tmp_path: FilePath) -> None:
    output_file = tmp_path / 'reports' / 'catalog.json'
    result = ddev('meta', 'catalog', '--format', 'json', '--output', str(output_file), 'postgres')

    assert result.exit_code == 0, result.output
    assert result.output == ''
    assert json.loads(output_file.read_text()) == {'targets': [RAW_TARGET_DESCRIPTIONS[0]], 'errors': []}


def test_json_output_with_errors_can_be_written_to_file(
    ddev: CliRunner, repository_as_cwd: ClonedRepo, tmp_path: FilePath
) -> None:
    output_file = tmp_path / 'catalog.json'
    result = ddev('meta', 'catalog', '--format', 'json', '--output', str(output_file), 'postgres', 'missing')

    assert result.exit_code == 1, result.output
    assert 'Errors encountered; see output file for details.' in result.output
    assert json.loads(output_file.read_text()) == {
        'targets': [RAW_TARGET_DESCRIPTIONS[0]],
        'errors': [{'target': 'missing', 'error': "Target 'missing' is not a directory or does not exist."}],
    }


def test_output_rejected_for_terminal_format(
    ddev: CliRunner, repository_as_cwd: ClonedRepo, tmp_path: FilePath
) -> None:
    result = ddev('meta', 'catalog', '--output', str(tmp_path / 'catalog.txt'), 'postgres')

    assert result.exit_code == 2, result.output
    assert '`--output` can only be used with non-terminal formats.' in result.output


def test_no_targets_exits_with_usage_error(ddev: CliRunner, repository_as_cwd: ClonedRepo) -> None:
    result = ddev('meta', 'catalog')

    assert result.exit_code == 2, result.output
    assert 'Missing argument' in result.output
