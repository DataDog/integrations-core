# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

import pytest


@pytest.mark.parametrize(
    'target, expected',
    [
        pytest.param('postgres', True, id='integration-package'),
        pytest.param('kubernetes', True, id='integration-tile'),
        pytest.param('ddev', False, id='package-not-integration'),
        pytest.param('docs', False, id='non-package-not-integration'),
    ],
)
def test_table_output(ddev, repository_as_cwd, target, expected):
    result = ddev('meta', 'describe', target)

    assert result.exit_code == 0, result.output
    assert target in result.output
    assert str(expected).lower() in result.output


def test_preserves_target_order(ddev, repository_as_cwd):
    targets = ['docs', 'ddev', 'kubernetes', 'postgres']
    result = ddev('meta', 'describe', *targets)

    assert result.exit_code == 0, result.output
    positions = [result.output.index(target) for target in targets]
    assert positions == sorted(positions)


@pytest.mark.parametrize(
    'target, expected',
    [
        pytest.param('postgres', True, id='integration-package'),
        pytest.param('kubernetes', True, id='integration-tile'),
        pytest.param('ddev', False, id='package-not-integration'),
        pytest.param('docs', False, id='non-package-not-integration'),
    ],
)
def test_json_output(ddev, repository_as_cwd, target, expected):
    result = ddev('meta', 'describe', '--json', target)

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == [{'path': target, 'is_integration': expected}]


def test_json_output_with_multiple_targets(ddev, repository_as_cwd):
    result = ddev('meta', 'describe', '--json', 'postgres', 'kubernetes', 'ddev', 'docs')

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == [
        {'path': 'postgres', 'is_integration': True},
        {'path': 'kubernetes', 'is_integration': True},
        {'path': 'ddev', 'is_integration': False},
        {'path': 'docs', 'is_integration': False},
    ]


def test_missing_directory(ddev, repository_as_cwd):
    result = ddev('meta', 'describe', 'missing')

    assert result.exit_code == 2, result.output
    assert "Directory 'missing' does not exist" in result.output
