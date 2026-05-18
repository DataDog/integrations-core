# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import httpx
import pytest
from pytest_mock import MockerFixture

from tests.helpers.github_async import DEFAULT_DISPATCH_HTML_URL, FakeAsyncGitHubClient
from tests.helpers.runner import CliRunner

EXPECTED_INPUTS = {
    'test-py3': 'true',
    'test-py2': 'false',
    'agent-image': 'registry.datadoghq.com/agent:7.80.0-rc.3',
    'agent-image-windows': 'registry.datadoghq.com/agent:7.80.0-rc.3-servercore',
}


@pytest.fixture(autouse=True)
def _silence_git(mocker: MockerFixture) -> None:
    """Default git mocks: ref exists on origin and both workflow files are present at the ref."""
    mocker.patch('ddev.utils.git.GitRepository.capture', return_value='abc123\trefs/heads/7.80.x\n')
    mocker.patch('ddev.utils.git.GitRepository.show_file', return_value='workflow yaml')


@pytest.fixture(autouse=True)
def _silence_registry(mocker: MockerFixture) -> None:
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
def test_input_validation(ddev: CliRunner, args: list[str], expected: str) -> None:
    result = ddev('release', 'test-agent', *args)
    assert result.exit_code != 0, result.output
    assert expected in result.output


def test_tag_with_leading_v_is_accepted(ddev: CliRunner, fake_async_github: FakeAsyncGitHubClient) -> None:
    result = ddev('release', 'test-agent', '--tag', 'v7.80.0-rc.1', '--yes')
    assert result.exit_code == 0, result.output
    call = fake_async_github.last_call('create_workflow_dispatch')
    assert call.kwargs['inputs']['agent-image'] == 'registry.datadoghq.com/agent:7.80.0-rc.1'


@pytest.mark.parametrize('workflow_id', ['test-agent.yml', 'test-agent-windows.yml'])
def test_branch_resolves_latest_rc_dispatches_both(
    ddev: CliRunner, fake_async_github: FakeAsyncGitHubClient, workflow_id: str
) -> None:
    result = ddev('release', 'test-agent', '--branch', '7.80.x', '--yes')

    assert result.exit_code == 0, result.output
    fake_async_github.assert_called_with(
        'create_workflow_dispatch',
        owner='DataDog',
        repo='integrations-core',
        workflow_id=workflow_id,
        ref='7.80.x',
        inputs=EXPECTED_INPUTS,
        timeout=None,
        return_run_details=True,
    )


@pytest.mark.parametrize('workflow_id', ['test-agent.yml', 'test-agent-windows.yml'])
def test_tag_dispatches_both(ddev: CliRunner, fake_async_github: FakeAsyncGitHubClient, workflow_id: str) -> None:
    """A bare `--tag` (no `v` prefix, no `-rc` suffix) must drive the same dispatch shape as `--branch`."""
    result = ddev('release', 'test-agent', '--tag', '7.80.0', '--yes')

    assert result.exit_code == 0, result.output
    fake_async_github.assert_called_with(
        'create_workflow_dispatch',
        owner='DataDog',
        repo='integrations-core',
        workflow_id=workflow_id,
        ref='7.80.0',
        inputs={
            'test-py3': 'true',
            'test-py2': 'false',
            'agent-image': 'registry.datadoghq.com/agent:7.80.0',
            'agent-image-windows': 'registry.datadoghq.com/agent:7.80.0-servercore',
        },
        timeout=None,
        return_run_details=True,
    )


def test_dry_run_does_not_dispatch(ddev: CliRunner, fake_async_github: FakeAsyncGitHubClient) -> None:
    result = ddev('release', 'test-agent', '--branch', '7.80.x', '--dry-run')

    assert result.exit_code == 0, result.output
    fake_async_github.assert_not_called('create_workflow_dispatch')
    assert 'Dry run' in result.output


def test_branch_with_no_rcs_aborts(
    ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient
) -> None:
    mocker.patch('ddev.cli.release.test_agent.registry.list_agent_rc_tags', return_value=[])

    result = ddev('release', 'test-agent', '--branch', '7.99.x', '--yes')

    assert result.exit_code != 0, result.output
    assert 'No `7.99.0-rc.*` tags found' in result.output
    fake_async_github.assert_not_called('create_workflow_dispatch')


def test_missing_image_aborts(ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient) -> None:
    mocker.patch('ddev.cli.release.test_agent.registry.manifest_exists', return_value=False)

    result = ddev('release', 'test-agent', '--tag', '9.99.0-rc.1', '--yes')

    assert result.exit_code != 0, result.output
    assert 'not found in registry.datadoghq.com' in result.output
    fake_async_github.assert_not_called('create_workflow_dispatch')


def test_missing_ref_aborts(ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient) -> None:
    mocker.patch('ddev.utils.git.GitRepository.capture', return_value='')

    result = ddev('release', 'test-agent', '--branch', '7.80.x', '--yes')

    assert result.exit_code != 0, result.output
    assert 'not found on origin' in result.output
    fake_async_github.assert_not_called('create_workflow_dispatch')


def test_missing_workflow_file_aborts(
    ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient
) -> None:
    """A 'file exists on disk, but not in <ref>' git error reads as the workflow really being absent."""
    mocker.patch(
        'ddev.utils.git.GitRepository.show_file',
        side_effect=OSError(
            "fatal: path '.github/workflows/test-agent.yml' exists on disk, but not in 'origin/7.80.x'"
        ),
    )

    result = ddev('release', 'test-agent', '--branch', '7.80.x', '--yes')

    assert result.exit_code != 0, result.output
    assert 'missing required workflow file' in result.output
    assert 'origin/7.80.x' in result.output
    fake_async_github.assert_not_called('create_workflow_dispatch')


def test_unfetched_branch_surfaces_fetch_hint(
    ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient
) -> None:
    """When `origin/<branch>` isn't in the local clone, the abort should tell the user to fetch."""
    mocker.patch(
        'ddev.utils.git.GitRepository.show_file',
        side_effect=OSError("fatal: invalid object name 'origin/7.80.x'"),
    )

    result = ddev('release', 'test-agent', '--branch', '7.80.x', '--yes')

    assert result.exit_code != 0, result.output
    assert 'not in your local clone' in result.output
    assert 'git fetch origin 7.80.x' in result.output
    fake_async_github.assert_not_called('create_workflow_dispatch')


def test_unknown_git_failure_surfaces_original_error(
    ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient
) -> None:
    """Anything we don't recognise from git must bubble up — never silently look like a missing workflow."""
    mocker.patch(
        'ddev.utils.git.GitRepository.show_file',
        side_effect=OSError('fatal: index file corrupt'),
    )

    result = ddev('release', 'test-agent', '--branch', '7.80.x', '--yes')

    assert result.exit_code != 0, result.output
    assert 'Failed to read' in result.output
    assert 'index file corrupt' in result.output
    fake_async_github.assert_not_called('create_workflow_dispatch')


@pytest.mark.parametrize(
    'failing_workflow, failing_label',
    [
        pytest.param('test-agent-windows.yml', 'Windows', id='windows-fails'),
        pytest.param('test-agent.yml', 'Linux', id='linux-fails'),
    ],
)
def test_partial_dispatch_failure_surfaces_sibling_url(
    ddev: CliRunner,
    fake_async_github: FakeAsyncGitHubClient,
    failing_workflow: str,
    failing_label: str,
) -> None:
    """When only one dispatch fails, the surviving side's URL must appear in the error message."""
    err = httpx.HTTPStatusError(
        'forbidden',
        request=httpx.Request('POST', 'https://api.github.com/'),
        response=httpx.Response(403),
    )
    fake_async_github.mock_response('create_workflow_dispatch', err, workflow_id=failing_workflow)

    result = ddev('release', 'test-agent', '--branch', '7.80.x', '--yes')

    assert result.exit_code != 0, result.output
    assert f'{failing_label} dispatch failed' in result.output
    assert DEFAULT_DISPATCH_HTML_URL in result.output


def test_both_dispatches_fail_combine_messages(ddev: CliRunner, fake_async_github: FakeAsyncGitHubClient) -> None:
    """Both-fail must announce itself explicitly and surface both error reprs, not just substrings.

    Asserting on `forbidden` appearing twice catches the previous regression where `add_note`
    was used to attach the Windows error — `str(exc)` does not include notes, so the Windows
    side was silently dropped from the abort message.
    """
    err = httpx.HTTPStatusError(
        'forbidden',
        request=httpx.Request('POST', 'https://api.github.com/'),
        response=httpx.Response(403),
    )
    fake_async_github.mock_response('create_workflow_dispatch', err)

    result = ddev('release', 'test-agent', '--branch', '7.80.x', '--yes')

    assert result.exit_code != 0, result.output
    assert 'Both dispatches failed' in result.output
    assert 'Linux:' in result.output
    assert 'Windows:' in result.output
    assert result.output.count('forbidden') == 2


def test_missing_github_token_aborts(ddev: CliRunner, mocker: MockerFixture, config_file) -> None:
    """The empty-token guard must abort before any dispatch attempt."""
    config_file.model.github.token = ''
    config_file.save()

    result = ddev('release', 'test-agent', '--branch', '7.80.x', '--yes')

    assert result.exit_code != 0, result.output
    assert 'GitHub token required' in result.output


@pytest.mark.parametrize(
    'mock_target, expected_message',
    [
        pytest.param(
            'ddev.cli.release.test_agent.registry.list_agent_rc_tags',
            'Failed to query registry.datadoghq.com for tags',
            id='list_tags',
        ),
        pytest.param(
            'ddev.cli.release.test_agent.registry.manifest_exists',
            'Failed to query registry.datadoghq.com for',
            id='manifest_exists',
        ),
    ],
)
def test_registry_http_error_aborts_cleanly(
    ddev: CliRunner,
    mocker: MockerFixture,
    fake_async_github: FakeAsyncGitHubClient,
    mock_target: str,
    expected_message: str,
) -> None:
    """A transient httpx error from the registry must surface via app.abort, not a raw traceback."""
    mocker.patch(mock_target, side_effect=httpx.ConnectError('connection refused'))

    result = ddev('release', 'test-agent', '--branch', '7.80.x', '--yes')

    assert result.exit_code != 0, result.output
    assert expected_message in result.output
    fake_async_github.assert_not_called('create_workflow_dispatch')
