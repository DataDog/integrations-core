# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json


def test_table_output(ddev, repository_as_cwd):
    result = ddev('meta', 'describe', 'postgres', 'ddev')

    assert result.exit_code == 0, result.output
    assert 'postgres' in result.output
    assert 'true' in result.output
    assert 'ddev' in result.output
    assert 'false' in result.output


def test_preserves_target_order(ddev, repository_as_cwd):
    result = ddev('meta', 'describe', 'ddev', 'postgres')

    assert result.exit_code == 0, result.output
    assert result.output.index('ddev') < result.output.index('postgres')


def test_json_output(ddev, repository_as_cwd):
    result = ddev('meta', 'describe', '--json', 'postgres', 'ddev')

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == [
        {'path': 'postgres', 'is_integration': True},
        {'path': 'ddev', 'is_integration': False},
    ]


def test_missing_directory(ddev, repository_as_cwd):
    result = ddev('meta', 'describe', 'missing')

    assert result.exit_code == 1, result.output
    assert 'Directory does not exist: missing' in result.output
