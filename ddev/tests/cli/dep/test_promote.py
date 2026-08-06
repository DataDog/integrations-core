# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import pytest

from ddev.cli.dep.promote import WorkflowRunLookup, most_recent_run
from ddev.utils.github_async.models import WorkflowRun

RUN_DETAILS = {
    'workflow_run_id': 999,
    'run_url': 'https://api.github.com/repos/DataDog/integrations-core/actions/runs/999',
    'html_url': 'https://github.com/DataDog/integrations-core/actions/runs/999',
}

RESOLUTION_RUN_URL = 'https://github.com/DataDog/integrations-core/actions/runs/555'


def resolution_workflow_run(status='completed', conclusion='success', **extra):
    """A `resolve-build-deps.yaml` run for the head commit the promote tests use."""
    return WorkflowRun(
        id=555,
        status=status,
        conclusion=conclusion,
        html_url=RESOLUTION_RUN_URL,
        head_sha='deadbeef',
        run_number=1,
        **extra,
    )


@pytest.fixture(autouse=True)
def resolution_run(mocker):
    """Default every test to a head commit whose resolution finished successfully."""
    return mocker.patch(
        'ddev.cli.dep.promote.WorkflowRunLookup.latest_run',
        return_value=resolution_workflow_run(),
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
    resolution_run.return_value = resolution_workflow_run(status=status, conclusion=None)
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
    resolution_run.return_value = resolution_workflow_run(conclusion=conclusion)
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


def workflow_run(run_number=1, html_url='u', **extra):
    return WorkflowRun(
        id=run_number,
        status='completed',
        conclusion='success',
        html_url=html_url,
        head_sha='deadbeef',
        run_number=run_number,
        **extra,
    )


@pytest.mark.parametrize(
    ('runs', 'expected_url'),
    [
        pytest.param([], None, id='no-runs'),
        pytest.param([workflow_run(run_number=4, html_url='u1')], 'u1', id='single-run'),
        pytest.param(
            [workflow_run(run_number=7, html_url='newest'), workflow_run(run_number=5, html_url='older')],
            'newest',
            id='highest-run-number-wins-regardless-of-order',
        ),
        pytest.param(
            [workflow_run(run_number=5, html_url='older'), workflow_run(run_number=7, html_url='newest')],
            'newest',
            id='api-order-is-not-trusted',
        ),
        pytest.param(
            [
                workflow_run(run_number=7, run_attempt=2, html_url='re-run'),
                workflow_run(run_number=7, run_attempt=1, html_url='first-attempt'),
            ],
            're-run',
            id='latest-attempt-of-the-same-run-wins',
        ),
        pytest.param(
            [
                workflow_run(run_number=7, run_attempt=2, html_url='re-run'),
                workflow_run(run_number=7, html_url='no-attempt'),
            ],
            're-run',
            id='absent-run-attempt-counts-as-zero',
        ),
    ],
)
def test_most_recent_run(runs, expected_url):
    """The most recent run for the commit is reported, or None when there are no runs."""
    result = most_recent_run(runs)

    assert (result.html_url if result else None) == expected_url


def test_workflow_run_lookup_reads_every_page_and_picks_the_latest(mocker):
    """The lookup must merge all pages before choosing, since page one can hide the newest run."""
    from ddev.utils.github_async import GitHubResponse
    from ddev.utils.github_async.models import WorkflowRunsList

    # The autouse fixture replaces `latest_run` itself, which is exactly what this test exercises.
    mocker.stopall()

    pages = [
        WorkflowRunsList(total_count=2, workflow_runs=[workflow_run(run_number=5, html_url='older')]),
        WorkflowRunsList(total_count=2, workflow_runs=[workflow_run(run_number=9, html_url='newest')]),
    ]
    captured = {}

    async def fake_list_workflow_runs(_self, **kwargs):
        captured.update(kwargs)
        for page in pages:
            yield GitHubResponse[WorkflowRunsList](data=page)

    mocker.patch(
        'ddev.utils.github_async.client.AsyncGitHubClient.list_workflow_runs',
        fake_list_workflow_runs,
    )

    lookup = WorkflowRunLookup(token='token', owner='DataDog', repo='integrations-core')
    result = lookup.latest_run('resolve-build-deps.yaml', 'deadbeef')

    assert result is not None
    assert result.html_url == 'newest'
    assert captured == {
        'owner': 'DataDog',
        'repo': 'integrations-core',
        'workflow_id': 'resolve-build-deps.yaml',
        'head_sha': 'deadbeef',
        'per_page': 100,
    }


def test_promote_restores_httpx_log_level_on_failure(ddev, mocker, httpx_at_debug):
    """Ensure the finally branch restores the previous httpx logger level even when an API call raises."""
    mocker.patch('ddev.utils.github.GitHubManager.get_pr_head', side_effect=RuntimeError('boom'))
    mocker.patch('ddev.utils.github.GitHubManager.dispatch_workflow')

    with pytest.raises(RuntimeError, match='boom'):
        ddev('dep', 'promote', 'https://github.com/DataDog/integrations-core/pull/12345')

    assert httpx_at_debug.level == logging.DEBUG
