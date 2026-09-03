# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for `ddev ci dispatch-tests`: how it resolves the run it is asked to test."""

from __future__ import annotations

import pytest

from ddev.utils.github_async import GitHubResponse
from ddev.utils.github_async.models import PullRequest, PullRequestFile
from tests.cli.ci.tests.helpers import make_batch, make_job

PR_NUMBER = 4242
HEAD_SHA = 'head-sha-aaa'


def pull_request(state: str = 'open', changed_files: int | None = 1) -> PullRequest:
    return PullRequest(
        number=PR_NUMBER,
        html_url=f'https://github.com/DataDog/integrations-core/pull/{PR_NUMBER}',
        state=state,
        head={'ref': 'hs/a-branch', 'sha': HEAD_SHA},
        base={'ref': 'a-target-branch', 'sha': 'base-sha-bbb'},
        changed_files=changed_files,
    )


def files_page(*files: PullRequestFile) -> GitHubResponse[list[PullRequestFile]]:
    return GitHubResponse[list[PullRequestFile]].model_validate({'data': list(files), 'headers': {}})


def pulls_page(*pulls: PullRequest) -> GitHubResponse[list[PullRequest]]:
    return GitHubResponse[list[PullRequest]].model_validate({'data': list(pulls), 'headers': {}})


@pytest.fixture
def planned(mocker):
    """Stand in for the planning layer, which has its own tests and costs a Hatch call per target."""
    batches = [make_batch(make_job(target='ntp'))]
    return mocker.patch('ddev.cli.ci.dispatch_tests.build_plan', return_value=batches)


@pytest.fixture
def local_changes(mocker):
    """Stand in for the git comparison, so a test about anything else needs no real commit.

    `changes_in_commit` is imported inside the function that calls it, so the patch lands on the
    defining module.
    """
    from ddev.utils.git import ChangedFile, ChangeType

    return mocker.patch(
        'ddev.cli.ci.tests.changes.changes_in_commit',
        return_value=[ChangedFile(ChangeType.MODIFIED, 'ntp/datadog_checks/ntp/ntp.py')],
    )


@pytest.fixture
def github(fake_async_github):
    """A GitHub answering with one open pull request that changed one file."""
    fake_async_github.mock_response('get_pull_request', pull_request())
    fake_async_github.mock_response(
        'list_pull_request_files',
        files_page(PullRequestFile(filename='ntp/datadog_checks/ntp/ntp.py', status='modified')),
    )
    return fake_async_github


@pytest.mark.parametrize(
    'reference',
    [PR_NUMBER, f'https://github.com/DataDog/integrations-core/pull/{PR_NUMBER}'],
    ids=['number', 'url'],
)
def test_a_pull_request_supplies_the_whole_run_context(ddev, github, planned, reference):
    """`--pr` is the only input a pull request run should need: everything else comes from the API."""
    result = ddev('ci', 'dispatch-tests', '--pr', str(reference), '--dry-run')

    assert result.exit_code == 0, result.output
    assert 'hs/a-branch' in result.output
    assert HEAD_SHA in result.output
    assert 'a-target-branch' in result.output
    # A pull request is tested at its merge commit, not at its head.
    assert f'refs/pull/{PR_NUMBER}/merge' in result.output


def test_a_head_sha_resolves_to_its_pull_request(ddev, github, planned):
    """`workflow_run` carries the head commit, not reliably a number, so the run resolves it."""
    github.mock_response('list_commit_pulls', pulls_page(pull_request()))

    result = ddev('ci', 'dispatch-tests', '--pr-head-sha', HEAD_SHA, '--dry-run')

    assert result.exit_code == 0, result.output
    assert str(PR_NUMBER) in result.output
    assert github.last_call('list_commit_pulls').kwargs['commit_sha'] == HEAD_SHA


def test_a_head_sha_belonging_to_no_open_pull_request_dispatches_nothing(ddev, github, planned):
    """A closed pull request resolves to nothing, and there is nothing to test or report to."""
    github.mock_response('list_commit_pulls', pulls_page())

    result = ddev('ci', 'dispatch-tests', '--pr-head-sha', HEAD_SHA)

    assert result.exit_code == 0, result.output
    assert 'belongs to no open pull request' in result.output
    planned.assert_not_called()
    github.assert_not_called('create_workflow_dispatch')


def test_a_pull_request_that_is_no_longer_open_dispatches_nothing(ddev, github, planned):
    """Nothing to test once it is closed, and no open pull request to comment on either."""
    github.mock_response('get_pull_request', pull_request(state='closed'))

    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER))

    assert result.exit_code == 0, result.output
    assert 'is not open' in result.output
    planned.assert_not_called()
    github.assert_not_called('create_workflow_dispatch')


def test_an_incomplete_diff_aborts_rather_than_testing_part_of_the_change(ddev, github, planned):
    """The files endpoint truncates silently, so a count that disagrees has to stop the run."""
    github.mock_response('get_pull_request', pull_request(changed_files=97))

    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER), '--dry-run')

    assert result.exit_code == 1
    assert 'reports 97 changed files but the API listed 1' in result.output
    planned.assert_not_called()


@pytest.mark.parametrize(
    'options',
    [
        ['--pr', str(PR_NUMBER), '--pr-head-sha', HEAD_SHA],
        ['--pr', str(PR_NUMBER), '--commit', 'a-sha'],
        ['--pr-head-sha', HEAD_SHA, '--commit', 'a-sha'],
    ],
    ids=['pr-and-head-sha', 'pr-and-commit', 'head-sha-and-commit'],
)
def test_only_one_run_can_be_named(ddev, github, planned, options: list[str]):
    """Taking one and ignoring the rest would test one commit and report against another."""
    result = ddev('ci', 'dispatch-tests', *options, '--dry-run')

    assert result.exit_code == 1
    assert 'name different runs' in result.output
    planned.assert_not_called()


def test_a_run_that_dispatches_needs_a_token_before_it_plans(ddev, planned, mocker):
    """Planning shells out to git and Hatch for every target, so a missing token must stop it first."""
    mocker.patch.dict('os.environ', {'DD_GITHUB_TOKEN': '', 'GH_TOKEN': '', 'GITHUB_TOKEN': ''})

    result = ddev('ci', 'dispatch-tests', '--commit', 'a-sha')

    assert result.exit_code == 1
    assert 'A GitHub token is required' in result.output
    planned.assert_not_called()


def test_a_dry_run_of_a_commit_needs_no_token(ddev, planned, local_changes, mocker):
    """The only run that talks to nobody: a commit is compared with its parent by local git."""
    mocker.patch.dict('os.environ', {'DD_GITHUB_TOKEN': '', 'GH_TOKEN': '', 'GITHUB_TOKEN': ''})

    result = ddev('ci', 'dispatch-tests', '--commit', 'a-sha', '--dry-run')

    assert result.exit_code == 0, result.output
    assert 'Dry run: nothing was dispatched.' in result.output


def test_a_dry_run_of_a_pull_request_needs_a_token(ddev, planned, mocker):
    """Its branch, commits and diff all come from the API, so there is no offline pull request run."""
    mocker.patch.dict('os.environ', {'DD_GITHUB_TOKEN': '', 'GH_TOKEN': '', 'GITHUB_TOKEN': ''})

    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER), '--dry-run')

    assert result.exit_code == 1
    assert 'A GitHub token is required' in result.output
    planned.assert_not_called()


def test_a_dry_run_dispatches_nothing(ddev, github, planned):
    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER), '--dry-run')

    assert result.exit_code == 0, result.output
    github.assert_not_called('create_workflow_dispatch')
    github.assert_not_called('create_issue_comment')


def test_a_reference_that_is_neither_a_number_nor_a_url_is_refused(ddev, planned):
    result = ddev('ci', 'dispatch-tests', '--pr', 'not-a-pull-request', '--dry-run')

    assert result.exit_code == 1
    assert 'neither a pull request number nor a pull request URL' in result.output
    planned.assert_not_called()


def test_an_empty_plan_is_not_dispatched(ddev, fake_async_github, local_changes, mocker):
    """Nothing to test is a clean outcome, not a failure and not an empty comment."""
    mocker.patch('ddev.cli.ci.dispatch_tests.build_plan', return_value=[])

    result = ddev('ci', 'dispatch-tests', '--commit', 'a-sha')

    assert result.exit_code == 0, result.output
    assert 'No affected target to test.' in result.output
    fake_async_github.assert_not_called('create_workflow_dispatch')


def test_all_targets_plans_without_reading_a_diff(ddev, github, planned):
    """`--all` decides which targets run without a comparison, so it reads no files."""
    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER), '--all', '--dry-run')

    assert result.exit_code == 0, result.output
    github.assert_not_called('list_pull_request_files')
    assert planned.call_args.kwargs['changed_files'] is None
