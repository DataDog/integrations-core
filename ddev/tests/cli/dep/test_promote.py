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


def test_promote_restores_httpx_log_level_on_failure(ddev, mocker, httpx_at_debug):
    """Ensure the finally branch restores the previous httpx logger level even when an API call raises."""
    mocker.patch('ddev.utils.github.GitHubManager.get_pr_head', side_effect=RuntimeError('boom'))
    mocker.patch('ddev.utils.github.GitHubManager.dispatch_workflow')

    with pytest.raises(RuntimeError, match='boom'):
        ddev('dep', 'promote', 'https://github.com/DataDog/integrations-core/pull/12345')

    assert httpx_at_debug.level == logging.DEBUG
