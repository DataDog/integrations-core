# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest


@pytest.mark.parametrize(
    'name',
    [
        pytest.param("7.5.2", id='does not end with ".x"'),
        pytest.param("7.5.6.x", id='too many parts'),
        pytest.param("7.x", id='not enough parts'),
    ],
)
def test_create_invalid_branch_name(ddev, name):
    result = ddev('release', 'branch', 'create', name)
    assert result.exit_code == 1, result.output
    assert f'Invalid branch name: {name}. Branch name must match the pattern ^\\d+\\.\\d+\\.x$\n' in result.output


def test_create_branch(ddev, mocker):
    run_mock = mocker.patch('ddev.utils.git.GitManager.run')
    create_label_mock = mocker.patch('ddev.utils.github.GitHubManager.create_label')

    result = ddev('release', 'branch', 'create', '5.5.x')

    assert result.exit_code == 0, result.output

    assert run_mock.call_args_list == [
        mocker.call('checkout', 'master'),
        mocker.call('pull', 'origin', 'master'),
        mocker.call('checkout', '-b', '5.5.x'),
        mocker.call('push', 'origin', '5.5.x'),
    ]

    assert create_label_mock.call_args_list == [
        mocker.call('backport/5.5.x', '5319e7'),
    ]
