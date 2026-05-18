# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import httpx
import pytest


@pytest.fixture(autouse=True)
def _silence_git(mocker):
    """Default git mocks: ref exists on origin and both workflow files are present at the ref."""
    mocker.patch('ddev.utils.git.GitRepository.capture', return_value='abc123\trefs/heads/7.80.x\n')
    mocker.patch('ddev.utils.git.GitRepository.show_file', return_value='workflow yaml')


@pytest.fixture(autouse=True)
def _silence_registry(mocker):
    """Default registry mocks: every manifest exists and there is one RC tag available."""
    mocker.patch('ddev.cli.release.test_agent.registry.manifest_exists', return_value=True)
    mocker.patch(
        'ddev.cli.release.test_agent.registry.list_agent_rc_tags',
        return_value=['7.80.0-rc.1', '7.80.0-rc.3'],
    )


@pytest.mark.parametrize(
    'args, expected',
    [
        pytest.param([], 'Exactly one of --branch or --tag', id='neither'),
        pytest.param(['--branch', '7.80.x', '--tag', '7.80.0'], 'Exactly one of --branch or --tag', id='both'),
        pytest.param(['--branch', '7.80'], 'Invalid branch', id='bad-branch'),
        pytest.param(['--tag', '7.80'], 'Invalid tag', id='bad-tag'),
    ],
)
def test_input_validation(ddev, args, expected):
    result = ddev('release', 'test-agent', *args)
    assert result.exit_code != 0, result.output
    assert expected in result.output


def test_tag_with_leading_v_is_accepted(ddev, fake_async_github):
    result = ddev('release', 'test-agent', '--tag', 'v7.80.0-rc.1', '--yes')
    assert result.exit_code == 0, result.output
    call = fake_async_github.last_call('create_workflow_dispatch')
    assert call.kwargs['inputs']['agent-image'] == 'registry.datadoghq.com/agent:7.80.0-rc.1'


def test_branch_resolves_latest_rc(ddev, fake_async_github):
    result = ddev('release', 'test-agent', '--branch', '7.80.x', '--yes')

    assert result.exit_code == 0, result.output
    linux_call = fake_async_github.assert_called_with(
        'create_workflow_dispatch',
        owner='DataDog',
        repo='integrations-core',
        workflow_id='test-agent.yml',
        ref='7.80.x',
        inputs={
            'test-py3': True,
            'test-py2': False,
            'agent-image': 'registry.datadoghq.com/agent:7.80.0-rc.3',
            'agent-image-windows': 'registry.datadoghq.com/agent:7.80.0-rc.3-servercore',
        },
        timeout=None,
        return_run_details=True,
    )
    assert linux_call is not None

    fake_async_github.assert_called_with(
        'create_workflow_dispatch',
        owner='DataDog',
        repo='integrations-core',
        workflow_id='test-agent-windows.yml',
        ref='7.80.x',
        inputs={
            'test-py3': True,
            'test-py2': False,
            'agent-image': 'registry.datadoghq.com/agent:7.80.0-rc.3',
            'agent-image-windows': 'registry.datadoghq.com/agent:7.80.0-rc.3-servercore',
        },
        timeout=None,
        return_run_details=True,
    )


def test_dry_run_does_not_dispatch(ddev, fake_async_github):
    result = ddev('release', 'test-agent', '--branch', '7.80.x', '--dry-run')

    assert result.exit_code == 0, result.output
    fake_async_github.assert_not_called('create_workflow_dispatch')
    assert 'Dry run' in result.output


def test_branch_with_no_rcs_aborts(ddev, mocker, fake_async_github):
    mocker.patch('ddev.cli.release.test_agent.registry.list_agent_rc_tags', return_value=[])

    result = ddev('release', 'test-agent', '--branch', '7.99.x', '--yes')

    assert result.exit_code != 0, result.output
    assert 'No `7.99.0-rc.*` tags found' in result.output
    fake_async_github.assert_not_called('create_workflow_dispatch')


def test_missing_image_aborts(ddev, mocker, fake_async_github):
    mocker.patch('ddev.cli.release.test_agent.registry.manifest_exists', return_value=False)

    result = ddev('release', 'test-agent', '--tag', '9.99.0-rc.1', '--yes')

    assert result.exit_code != 0, result.output
    assert 'not found in registry.datadoghq.com' in result.output
    fake_async_github.assert_not_called('create_workflow_dispatch')


def test_missing_ref_aborts(ddev, mocker, fake_async_github):
    mocker.patch('ddev.utils.git.GitRepository.capture', return_value='')

    result = ddev('release', 'test-agent', '--branch', '7.80.x', '--yes')

    assert result.exit_code != 0, result.output
    assert 'not found on origin' in result.output
    fake_async_github.assert_not_called('create_workflow_dispatch')


def test_missing_workflow_file_aborts(ddev, mocker, fake_async_github):
    mocker.patch('ddev.utils.git.GitRepository.show_file', side_effect=OSError('not in tree'))

    result = ddev('release', 'test-agent', '--branch', '7.80.x', '--yes')

    assert result.exit_code != 0, result.output
    assert 'missing required workflow file' in result.output
    fake_async_github.assert_not_called('create_workflow_dispatch')


def test_partial_dispatch_failure_surfaces_sibling_url(ddev, mocker, fake_async_github):
    """If the Windows dispatch raises after Linux succeeds, the Linux URL should be in the error message."""
    err = httpx.HTTPStatusError(
        'forbidden',
        request=httpx.Request('POST', 'https://api.github.com/'),
        response=httpx.Response(403),
    )
    fake_async_github.mock_response('create_workflow_dispatch', err, workflow_id='test-agent-windows.yml')

    result = ddev('release', 'test-agent', '--branch', '7.80.x', '--yes')

    assert result.exit_code != 0, result.output
    assert 'Windows dispatch failed' in result.output
    assert 'https://github.com/test/repo/actions/runs/1' in result.output
