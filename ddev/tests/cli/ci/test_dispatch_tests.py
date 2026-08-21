# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for `ddev ci dispatch-tests`: how it resolves the run it is asked to test."""

from __future__ import annotations

import pytest

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


def test_an_explicit_value_wins_over_the_resolved_one(ddev, github, planned):
    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER), '--base-sha', 'my-own-sha', '--dry-run')

    assert result.exit_code == 0, result.output
    assert 'my-own-sha' in result.output
    assert 'head-sha-aaa' not in result.output


def test_a_dry_run_dispatches_nothing(ddev, github, planned):
    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER), '--dry-run')

    assert result.exit_code == 0, result.output
    github.assert_not_called('create_workflow_dispatch')
    github.assert_not_called('create_issue_comment')


def test_a_reference_that_is_neither_a_number_nor_a_url_is_refused(ddev, planned):
    result = ddev('ci', 'dispatch-tests', '--pr', 'not-a-pull-request', '--dry-run')

    assert result.exit_code == 1
    assert 'neither a pull request number nor a pull request URL' in result.output


def test_an_empty_plan_is_not_dispatched(ddev, fake_async_github, mocker):
    """Nothing to test is a clean outcome, not a failure and not an empty comment."""
    mocker.patch('ddev.cli.ci.dispatch_tests.build_plan', return_value=[])

    result = ddev('ci', 'dispatch-tests', '--base-sha', 'a-sha')

    assert result.exit_code == 0, result.output
    assert 'No affected target to test.' in result.output
    fake_async_github.assert_not_called('create_workflow_dispatch')


def test_the_context_option_offers_every_run_context():
    """`--context` restates its choices as literals: `RunContext` lives in a module too heavy to
    import while building the decorator, so a member added there must not be left unreachable.
    """
    from ddev.cli.ci.dispatch_tests import dispatch_tests
    from ddev.cli.ci.tests.dispatcher import RunContext

    option = next(param for param in dispatch_tests.params if param.name == 'run_context')

    assert set(option.type.choices) == {member.value for member in RunContext}
