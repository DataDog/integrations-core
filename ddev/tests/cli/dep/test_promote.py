# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import pytest

RUN_DETAILS = {
    'workflow_run_id': 999,
    'run_url': 'https://api.github.com/repos/DataDog/integrations-core/actions/runs/999',
    'html_url': 'https://github.com/DataDog/integrations-core/actions/runs/999',
}

RESOLUTION_RUN_URL = 'https://github.com/DataDog/integrations-core/actions/runs/555'
SUCCESSFUL_RESOLUTION_RUN = {'status': 'completed', 'conclusion': 'success', 'html_url': RESOLUTION_RUN_URL}


@pytest.fixture(autouse=True)
def resolution_run(mocker):
    """Default every test to a head commit whose resolution finished successfully."""
    return mocker.patch(
        'ddev.utils.github.GitHubManager.get_latest_workflow_run',
        return_value=SUCCESSFUL_RESOLUTION_RUN,
    )


@pytest.fixture(autouse=True)
def from_fork(mocker):
    """Default every test to a pull request whose head branch lives in this repository."""
    return mocker.patch('ddev.utils.github.GitHubManager.pull_request_is_from_fork', return_value=False)


def test_promote_dispatches_workflow_and_prints_run_url(ddev, mocker):
    mocker.patch('ddev.utils.github.GitHubManager.get_pr_head', return_value=('deadbeef', 'feature-branch'))
    dispatch = mocker.patch('ddev.utils.github.GitHubManager.dispatch_workflow', return_value=RUN_DETAILS)

    result = ddev('dep', 'promote', 'https://github.com/DataDog/integrations-core/pull/12345')

    assert result.exit_code == 0, result.output
    dispatch.assert_called_once_with(
        workflow_id='dependency-wheel-promotion.yaml',
        ref='master',
        inputs={'pr_number': '12345', 'head_sha': 'deadbeef'},
        return_run_details=True,
    )
    assert 'PR #12345' in result.output
    assert 'feature-branch' in result.output
    assert 'deadbeef' in result.output
    assert RUN_DETAILS['html_url'] in result.output
    assert 'Recent runs' not in result.output
    assert 'query=event%3Aworkflow_dispatch' not in result.output


def test_promote_invalid_pr_url_aborts(ddev):
    result = ddev('dep', 'promote', 'https://example.invalid/not-a-pr')

    assert result.exit_code != 0
    assert 'Could not extract a PR number' in result.output


def test_promote_aborts_when_no_run_details_returned(ddev, mocker):
    mocker.patch('ddev.utils.github.GitHubManager.get_pr_head', return_value=('deadbeef', 'feature-branch'))
    mocker.patch('ddev.utils.github.GitHubManager.dispatch_workflow', return_value=None)

    result = ddev('dep', 'promote', 'https://github.com/DataDog/integrations-core/pull/12345')

    assert result.exit_code != 0
    assert 'no run details were returned' in result.output
    assert 'Promote workflow dispatched' not in result.output


def test_promote_suppresses_httpx_logs_and_restores_level(ddev, mocker, httpx_at_debug):
    captured_levels = []

    def capture_level(*_args, **_kwargs):
        captured_levels.append(httpx_at_debug.level)
        return ('deadbeef', 'feature-branch')

    mocker.patch('ddev.utils.github.GitHubManager.get_pr_head', side_effect=capture_level)
    mocker.patch('ddev.utils.github.GitHubManager.dispatch_workflow', return_value=RUN_DETAILS)

    result = ddev('dep', 'promote', 'https://github.com/DataDog/integrations-core/pull/12345')

    assert result.exit_code == 0, result.output
    assert captured_levels == [logging.WARNING]
    assert httpx_at_debug.level == logging.DEBUG


def test_promote_checks_resolution_for_the_head_commit(ddev, mocker, resolution_run):
    mocker.patch('ddev.utils.github.GitHubManager.get_pr_head', return_value=('deadbeef', 'feature-branch'))
    mocker.patch('ddev.utils.github.GitHubManager.dispatch_workflow', return_value=RUN_DETAILS)

    result = ddev('dep', 'promote', 'https://github.com/DataDog/integrations-core/pull/12345')

    assert result.exit_code == 0, result.output
    resolution_run.assert_called_once_with('resolve-build-deps.yaml', 'deadbeef')


@pytest.mark.parametrize('status', ['queued', 'in_progress'])
def test_promote_refuses_while_resolution_is_running(ddev, mocker, resolution_run, status):
    """Promotion copies whatever is in dev storage, so it must wait for the lockfiles."""
    resolution_run.return_value = {'status': status, 'conclusion': None, 'html_url': RESOLUTION_RUN_URL}
    mocker.patch('ddev.utils.github.GitHubManager.get_pr_head', return_value=('deadbeef', 'feature-branch'))
    dispatch = mocker.patch('ddev.utils.github.GitHubManager.dispatch_workflow')

    result = ddev('dep', 'promote', 'https://github.com/DataDog/integrations-core/pull/12345')

    assert result.exit_code != 0
    assert 'still running for deadbeef' in result.output
    assert RESOLUTION_RUN_URL in result.output
    assert 'Wait for it to commit the lockfiles' in result.output
    dispatch.assert_not_called()


@pytest.mark.parametrize('conclusion', ['failure', 'cancelled', 'timed_out', 'startup_failure', None])
def test_promote_refuses_when_resolution_did_not_succeed(ddev, mocker, resolution_run, conclusion):
    """A run that finished without publishing leaves the previous lockfiles at the head."""
    resolution_run.return_value = {'status': 'completed', 'conclusion': conclusion, 'html_url': RESOLUTION_RUN_URL}
    mocker.patch('ddev.utils.github.GitHubManager.get_pr_head', return_value=('deadbeef', 'feature-branch'))
    dispatch = mocker.patch('ddev.utils.github.GitHubManager.dispatch_workflow')

    result = ddev('dep', 'promote', 'https://github.com/DataDog/integrations-core/pull/12345')

    assert result.exit_code != 0
    assert 'did not succeed for deadbeef' in result.output
    assert RESOLUTION_RUN_URL in result.output
    assert 'Re-run it' in result.output
    dispatch.assert_not_called()


def test_promote_proceeds_when_resolution_never_ran(ddev, mocker, resolution_run):
    """An absent run says nothing about the lockfiles, so it must not block promotion."""
    resolution_run.return_value = None
    mocker.patch('ddev.utils.github.GitHubManager.get_pr_head', return_value=('deadbeef', 'feature-branch'))
    dispatch = mocker.patch('ddev.utils.github.GitHubManager.dispatch_workflow', return_value=RUN_DETAILS)

    result = ddev('dep', 'promote', 'https://github.com/DataDog/integrations-core/pull/12345')

    assert result.exit_code == 0, result.output
    dispatch.assert_called_once()


def test_promote_refuses_a_fork_pull_request(ddev, mocker, from_fork, resolution_run):
    """Resolution never runs on a fork, so promoting one publishes the base branch's wheels."""
    from_fork.return_value = True
    mocker.patch('ddev.utils.github.GitHubManager.get_pr_head', return_value=('deadbeef', 'feature-branch'))
    dispatch = mocker.patch('ddev.utils.github.GitHubManager.dispatch_workflow')

    result = ddev('dep', 'promote', 'https://github.com/DataDog/integrations-core/pull/12345')

    assert result.exit_code != 0
    assert 'comes from a fork' in result.output
    assert 'Reopen the change as a branch in this repository' in result.output
    dispatch.assert_not_called()
    resolution_run.assert_not_called()


def test_promote_restores_httpx_log_level_on_failure(ddev, mocker, httpx_at_debug):
    """Ensure the finally branch restores the previous httpx logger level even when an API call raises."""
    mocker.patch('ddev.utils.github.GitHubManager.get_pr_head', side_effect=RuntimeError('boom'))
    mocker.patch('ddev.utils.github.GitHubManager.dispatch_workflow')

    with pytest.raises(RuntimeError, match='boom'):
        ddev('dep', 'promote', 'https://github.com/DataDog/integrations-core/pull/12345')

    assert httpx_at_debug.level == logging.DEBUG
