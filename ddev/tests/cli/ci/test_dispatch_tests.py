# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for `ddev ci dispatch-tests`: how it resolves the run it is asked to test."""

from __future__ import annotations

import pytest

from ddev.cli.ci.tests.dispatcher import RunContext
from ddev.utils.github_async.models import PullRequest
from tests.cli.ci.tests.helpers import make_batch, make_job

PR_NUMBER = 4242
PR_PAYLOAD = PullRequest(
    number=PR_NUMBER,
    html_url=f'https://github.com/DataDog/integrations-core/pull/{PR_NUMBER}',
    head={'ref': 'hs/a-branch', 'sha': 'head-sha-aaa'},
    base={'ref': 'a-target-branch', 'sha': 'base-sha-bbb'},
)


@pytest.fixture
def planned(mocker):
    """Stand in for the planning layer, which has its own tests and costs a Hatch call per target."""
    batches = [make_batch(make_job(target='ntp'))]
    return mocker.patch('ddev.cli.ci.dispatch_tests.build_plan', return_value=batches)


@pytest.fixture
def github(fake_async_github):
    """A GitHub that answers `get_pull_request` with `PR_PAYLOAD`."""
    fake_async_github.mock_response('get_pull_request', PR_PAYLOAD)
    return fake_async_github


@pytest.mark.parametrize(
    'reference',
    [PR_NUMBER, f'https://github.com/DataDog/integrations-core/pull/{PR_NUMBER}'],
    ids=['number', 'url'],
)
def test_a_pull_request_supplies_the_run_context(ddev, github, planned, reference):
    """`--pr` is the only input a local run should need: everything else comes from the API."""
    result = ddev('ci', 'dispatch-tests', '--pr', str(reference), '--dry-run')

    assert result.exit_code == 0, result.output
    assert 'hs/a-branch' in result.output
    assert 'head-sha-aaa' in result.output
    assert 'a-target-branch' in result.output
    # A pull request is tested at its merge commit, not at its head.
    assert f'refs/pull/{PR_NUMBER}/merge' in result.output


@pytest.mark.parametrize(
    'option, value',
    [('--pr-number', '77'), ('--branch', 'a-branch'), ('--base-sha', 'a-sha'), ('--target-branch', 'a-target')],
)
def test_what_a_pull_request_resolves_cannot_also_be_passed(ddev, github, planned, option, value):
    """Taking one and ignoring the other would run one pull request's branch against another's diff."""
    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER), option, value, '--dry-run')

    assert result.exit_code == 1
    assert f'`{option}` cannot be passed with `--pr`' in result.output
    planned.assert_not_called()


def test_a_run_that_dispatches_needs_a_token_before_it_plans(ddev, planned, mocker):
    """Planning shells out to git and Hatch for every target, so a missing token must stop it first."""
    mocker.patch.dict('os.environ', {'DD_GITHUB_TOKEN': '', 'GH_TOKEN': '', 'GITHUB_TOKEN': ''})

    result = ddev('ci', 'dispatch-tests', '--base-sha', 'a-sha')

    assert result.exit_code == 1
    assert 'A GitHub token is required' in result.output
    planned.assert_not_called()


def test_a_dry_run_reading_no_pull_request_needs_no_token(ddev, planned, mocker):
    """The only run that talks to nobody, so it is the one exception to needing a token."""
    mocker.patch.dict('os.environ', {'DD_GITHUB_TOKEN': '', 'GH_TOKEN': '', 'GITHUB_TOKEN': ''})

    result = ddev('ci', 'dispatch-tests', '--base-sha', 'a-sha', '--dry-run')

    assert result.exit_code == 0, result.output
    assert 'Dry run: nothing was dispatched.' in result.output


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


def test_an_empty_plan_is_not_dispatched(ddev, fake_async_github, mocker):
    """Nothing to test is a clean outcome, not a failure and not an empty comment."""
    mocker.patch('ddev.cli.ci.dispatch_tests.build_plan', return_value=[])

    result = ddev('ci', 'dispatch-tests', '--base-sha', 'a-sha')

    assert result.exit_code == 0, result.output
    assert 'No affected target to test.' in result.output
    fake_async_github.assert_not_called('create_workflow_dispatch')


@pytest.mark.parametrize('run_context', list(RunContext), ids=lambda member: member.value)
def test_every_run_context_is_accepted(ddev, github, planned, run_context):
    """`--context` restates its choices as literals, because `RunContext` lives in a module too
    heavy to import while building the decorator. Parameterizing over the enum catches a member
    added there and never wired up.
    """
    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER), '--context', run_context.value, '--dry-run')

    assert result.exit_code == 0, result.output
    assert f'Context -> {run_context.value}' in result.output
