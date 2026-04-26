# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

import pytest

TARGET_DESCRIPTIONS = [
    pytest.param(
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
        id='integration-package',
    ),
    pytest.param(
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
        id='integration-tile',
    ),
    pytest.param(
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
        id='package-not-integration',
    ),
    pytest.param(
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
        id='non-package-not-integration',
    ),
]


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
        'Agent',
        'JMX',
        'Metrics',
    ):
        assert header in result.output


def test_preserves_target_order(ddev, repository_as_cwd):
    targets = ['docs', 'ddev', 'kubernetes', 'postgres']
    result = ddev('meta', 'catalog', '--json', *targets)

    assert result.exit_code == 0, result.output
    assert [description['path'] for description in json.loads(result.output)] == targets


@pytest.mark.parametrize('expected', TARGET_DESCRIPTIONS)
def test_json_output(ddev, repository_as_cwd, expected):
    result = ddev('meta', 'catalog', '--json', expected['path'])

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == [expected]


def test_json_output_with_multiple_targets(ddev, repository_as_cwd):
    result = ddev('meta', 'catalog', '--json', 'postgres', 'kubernetes', 'ddev', 'docs')

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == [param.values[0] for param in TARGET_DESCRIPTIONS]


def test_all_targets(ddev, repository_as_cwd):
    result = ddev('meta', 'catalog', '--json', 'all')

    assert result.exit_code == 0, result.output
    descriptions = json.loads(result.output)
    assert {'postgres', 'kubernetes'} <= {description['path'] for description in descriptions}
    assert 'ddev' not in {description['path'] for description in descriptions}
    assert all(description['is_integration'] for description in descriptions)


def test_all_cannot_be_combined_with_other_targets(ddev, repository_as_cwd):
    result = ddev('meta', 'catalog', 'all', 'postgres')

    assert result.exit_code == 2, result.output
    assert 'The `all` target cannot be combined with other targets.' in result.output


def test_missing_directory(ddev, repository_as_cwd):
    result = ddev('meta', 'catalog', 'missing')

    assert result.exit_code == 2, result.output
    assert "Directory 'missing' does not exist" in result.output
