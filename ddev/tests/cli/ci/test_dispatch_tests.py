# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for `ddev ci dispatch-tests`: how it resolves the run it is asked to test."""

from __future__ import annotations

import pytest

from ddev.utils.github_async import GitHubResponse
from ddev.utils.github_async.models import PullRequest, PullRequestFile, PullRequestSimple
from tests.cli.ci.tests.helpers import make_batch, make_job

PR_NUMBER = 4242
HEAD_SHA = 'head-sha-aaa'


def pull_request(
    state: str = 'open',
    changed_files: int = 1,
    number: int = PR_NUMBER,
    head_sha: str = HEAD_SHA,
    base_ref: str = 'a-target-branch',
) -> PullRequest:
    return PullRequest(
        number=number,
        html_url=f'https://github.com/DataDog/integrations-core/pull/{number}',
        state=state,
        head={'ref': 'hs/a-branch', 'sha': head_sha},
        base={'ref': base_ref, 'sha': 'base-sha-bbb'},
        changed_files=changed_files,
    )


def listed_pull_request(
    number: int = PR_NUMBER,
    head_sha: str = HEAD_SHA,
    base_ref: str = 'a-target-branch',
    state: str = 'open',
) -> PullRequestSimple:
    """What `list_commit_pulls` returns: no diff totals, so it cannot stand in for the full form."""
    return PullRequestSimple(
        number=number,
        html_url=f'https://github.com/DataDog/integrations-core/pull/{number}',
        state=state,
        head={'ref': 'hs/a-branch', 'sha': head_sha},
        base={'ref': base_ref, 'sha': 'base-sha-bbb'},
    )


def files_page(*files: PullRequestFile) -> GitHubResponse[list[PullRequestFile]]:
    return GitHubResponse[list[PullRequestFile]].model_validate({'data': list(files), 'headers': {}})


def pulls_page(*pulls: PullRequestSimple) -> GitHubResponse[list[PullRequestSimple]]:
    return GitHubResponse[list[PullRequestSimple]].model_validate({'data': list(pulls), 'headers': {}})


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
    github.mock_response('list_commit_pulls', pulls_page(listed_pull_request()))

    result = ddev('ci', 'dispatch-tests', '--pr-head-sha', HEAD_SHA, '--dry-run')

    assert result.exit_code == 0, result.output
    assert str(PR_NUMBER) in result.output
    assert github.last_call('list_commit_pulls').kwargs['commit_sha'] == HEAD_SHA


def test_a_head_sha_belonging_to_no_open_pull_request_dispatches_nothing(ddev, github, planned):
    github.mock_response('list_commit_pulls', pulls_page())

    result = ddev('ci', 'dispatch-tests', '--pr-head-sha', HEAD_SHA)

    assert result.exit_code == 0, result.output
    assert 'heads no open pull request' in result.output
    planned.assert_not_called()
    github.assert_not_called('create_workflow_dispatch')


def test_a_commit_that_is_no_longer_the_head_dispatches_nothing(ddev, github, planned):
    """A commit stays associated with its pull request once later commits land on the branch.

    Testing it anyway would read the newer head and diff while reporting against the older commit,
    so the run would test one revision and attribute it to another.
    """
    github.mock_response('list_commit_pulls', pulls_page(listed_pull_request(head_sha='a-newer-sha')))

    result = ddev('ci', 'dispatch-tests', '--pr-head-sha', HEAD_SHA)

    assert result.exit_code == 0, result.output
    assert 'heads no open pull request' in result.output
    planned.assert_not_called()
    github.assert_not_called('create_workflow_dispatch')


def test_a_head_that_moves_while_the_pull_request_is_read_dispatches_nothing(ddev, github, planned):
    """The number is resolved from one response and the pull request read from another.

    A commit pushed in between leaves the second describing a newer revision, whose diff and head
    would then be tested and reported against the commit this run was asked for.
    """
    github.mock_response('list_commit_pulls', pulls_page(listed_pull_request()))
    github.mock_response('get_pull_request', pull_request(head_sha='a-newer-sha'))

    result = ddev('ci', 'dispatch-tests', '--pr-head-sha', HEAD_SHA)

    assert result.exit_code == 0, result.output
    assert f'has moved on from {HEAD_SHA}' in result.output
    planned.assert_not_called()
    github.assert_not_called('create_workflow_dispatch')


def test_a_head_sha_heading_several_pull_requests_is_refused(ddev, github, planned):
    """Choosing one would plan against its base and comment on it, so a run that cannot say which
    pull request it is testing must not run.
    """
    github.mock_response(
        'list_commit_pulls',
        pulls_page(listed_pull_request(number=1), listed_pull_request(number=2, base_ref='7.62.x')),
    )

    result = ddev('ci', 'dispatch-tests', '--pr-head-sha', HEAD_SHA)

    assert result.exit_code == 1
    assert 'heads 2 open pull requests (#1, #2)' in result.output
    planned.assert_not_called()
    github.assert_not_called('create_workflow_dispatch')


def test_a_base_ref_narrows_an_ambiguous_head_sha(ddev, github, planned):
    github.mock_response(
        'list_commit_pulls',
        pulls_page(listed_pull_request(number=1), listed_pull_request(number=2, base_ref='7.62.x')),
    )
    github.mock_response('get_pull_request', pull_request(number=2, base_ref='7.62.x'))

    result = ddev('ci', 'dispatch-tests', '--pr-head-sha', HEAD_SHA, '--pr-base-ref', '7.62.x', '--dry-run')

    assert result.exit_code == 0, result.output
    assert github.last_call('get_pull_request').kwargs['pull_number'] == 2


def test_a_base_ref_without_a_head_sha_is_refused(ddev, github, planned):
    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER), '--pr-base-ref', 'master', '--dry-run')

    assert result.exit_code == 2
    assert 'only narrows which pull request' in result.output
    planned.assert_not_called()


def test_a_pull_request_that_is_no_longer_open_dispatches_nothing(ddev, github, planned):
    """Nothing to test at that point, and no open pull request to report to either."""
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

    assert result.exit_code == 2
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
    """The only run that talks to nobody, since git answers the comparison."""
    mocker.patch.dict('os.environ', {'DD_GITHUB_TOKEN': '', 'GH_TOKEN': '', 'GITHUB_TOKEN': ''})

    result = ddev('ci', 'dispatch-tests', '--commit', 'a-sha', '--dry-run')

    assert result.exit_code == 0, result.output
    assert 'Dry run: nothing was dispatched.' in result.output


def test_a_dry_run_of_a_pull_request_needs_a_token(ddev, planned, mocker):
    """Its branch, commits and diff all come from the API, so there is no offline version of it."""
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

    assert result.exit_code == 2
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
    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER), '--all', '--dry-run')

    assert result.exit_code == 0, result.output
    github.assert_not_called('list_pull_request_files')
    assert planned.call_args.kwargs['changed_files'] is None
