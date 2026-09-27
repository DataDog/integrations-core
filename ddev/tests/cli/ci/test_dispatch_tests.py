# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for `ddev ci dispatch-tests`: how it resolves the run it is asked to test."""

from __future__ import annotations

import json
import logging
import subprocess
from collections import Counter
from functools import partial
from typing import TYPE_CHECKING, Any
from unittest.mock import ANY

import httpx
import pytest

from ddev.cli.application import Application
from ddev.cli.ci.dispatch_run import resolve_run
from ddev.cli.ci.dispatch_tests import attach_datadog_log_handler
from ddev.cli.ci.tests.batching.exceptions import PlanningError
from ddev.cli.ci.tests.dispatcher_attributes import metric_tag_mapping
from ddev.cli.ci.tests.dispatcher_config import DispatcherConfig
from ddev.cli.ci.tests.dispatcher_logging import dispatcher_datadog_formatter
from ddev.monitoring import MonitoringRuntime
from ddev.monitoring.datadog import DatadogLogHandler
from ddev.monitoring.datadog_metrics import DatadogMetricsSink
from ddev.utils.git import ChangedFile, ChangeType, GitCommit
from ddev.utils.github_async import async_github_client
from ddev.utils.github_async.models import PullRequest, PullRequestState
from ddev.utils.rate_limiting import BudgetGovernor
from tests.cli.ci.helpers import HEAD_SHA, PR_NUMBER, decode_job_list, listed_pull_request, mock_job_result, pulls_page
from tests.cli.ci.tests.helpers import make_batch, make_job
from tests.helpers.clock import FakeClock, advance_clock_on_sleep
from tests.helpers.datadog import FakeLogSubmitter, FakeMetricsSubmitter
from tests.helpers.github_async import (
    make_pull_request,
    make_pull_request_ref,
    make_pull_request_repo,
    make_workflow_run,
)
from tests.helpers.monitoring import RecordingJsonHandler, RecordingSink, projector_for

if TYPE_CHECKING:
    from pathlib import Path
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture

    from ddev.cli.application import Application
    from ddev.cli.ci.dispatch_run import ResolvedRun
    from ddev.cli.ci.tests.messages import TestBatch
    from ddev.config.file import ConfigFileWithOverrides
    from ddev.monitoring import ComponentMonitor
    from tests.helpers.github_async import FakeAsyncGitHubClient
    from tests.helpers.runner import CliRunner

HEAD_LOOKUP_OPTIONS = (
    '--pr-head-sha',
    HEAD_SHA,
    '--pr-head-repo',
    'DataDog/integrations-core',
    '--pr-head-branch',
    'hs/a-branch',
)

MERGE_SHA = 'merge-sha-mmm'
BASE_SHA = 'base-sha-bbb'
# GitHub's base snapshot may lag the first parent used for the synthetic merge.
PARENTS = {f'{MERGE_SHA}^1': 'current-master-sha-ccc', f'{MERGE_SHA}^2': HEAD_SHA}


def pull_request(
    state: PullRequestState = PullRequestState.OPEN,
    number: int = PR_NUMBER,
    head_sha: str = HEAD_SHA,
    base_branch: str = 'a-target-branch',
    base_sha: str = BASE_SHA,
    head_repo: str | None = 'DataDog/integrations-core',
    merge_commit_sha: str | None = MERGE_SHA,
) -> PullRequest:
    return make_pull_request(
        number=number,
        state=state,
        head=make_pull_request_ref(
            ref='hs/a-branch',
            sha=head_sha,
            repo=None if head_repo is None else make_pull_request_repo(full_name=head_repo),
        ),
        base=make_pull_request_ref(ref=base_branch, sha=base_sha, repo=None),
        merge_commit_sha=merge_commit_sha,
    )


@pytest.fixture
def planned(mocker):
    """Keep PR-resolution tests independent of the planning layer."""
    batches = [make_batch(make_job(target='ntp'))]
    return mocker.patch('ddev.cli.ci.dispatch_tests.build_plan', return_value=batches)


@pytest.fixture
def local_changes(mocker):
    """Stand in for the git comparison, so a test about anything else needs no real commit."""
    return mocker.patch(
        'ddev.cli.ci.tests.changes.changes_in_commit',
        return_value=[ChangedFile(ChangeType.MODIFIED, 'ntp/datadog_checks/ntp/ntp.py')],
    )


@pytest.fixture
def resolved_changes(mocker):
    """Stand in for the whole comparison boundary, so a test about anything else needs no checkout."""
    return mocker.patch(
        'ddev.cli.ci.dispatch_tests.changes_for_run',
        return_value=[ChangedFile(ChangeType.MODIFIED, 'ntp/datadog_checks/ntp/ntp.py')],
    )


@pytest.fixture
def github(fake_async_github, resolved_changes):
    """A GitHub answering with one open pull request, and a comparison that needs no checkout."""
    fake_async_github.mock_response('get_pull_request', pull_request())
    return fake_async_github


@pytest.mark.parametrize(
    'options',
    [
        ['--pr', str(PR_NUMBER)],
        ['--pr', f'https://github.com/DataDog/integrations-core/pull/{PR_NUMBER}'],
        ['--pr', str(PR_NUMBER), '--pr-head-sha', HEAD_SHA],
        ['--pr', str(PR_NUMBER), '--pr-head-branch', 'hs/a-branch'],
        ['--pr', str(PR_NUMBER), '--pr-base-branch', 'a-target-branch'],
    ],
    ids=['number', 'url', 'number-with-expected-head', 'number-with-head-constraint', 'number-with-base-constraint'],
)
def test_a_pull_request_supplies_the_whole_run_context(ddev, github, planned, options: list[str]):
    """The PR supplies the context; an optional expected head constrains which revision is accepted."""
    result = ddev('ci', 'dispatch-tests', *options, '--dry-run')

    assert result.exit_code == 0, result.output
    assert 'hs/a-branch' in result.output
    assert HEAD_SHA in result.output
    assert 'a-target-branch' in result.output
    # A pull request is tested at its immutable merge commit, not at its head.
    assert MERGE_SHA in result.output


def test_dispatch_tests_plans_from_testable_target(
    ddev: CliRunner, github: FakeAsyncGitHubClient, config_file: ConfigFileWithOverrides, tmp_path: Path
):
    root = tmp_path / 'repo'
    (root / '.ddev').mkdir(parents=True)
    (root / '.ddev' / 'config.toml').write_text('')
    subprocess.run(['git', 'init', '--quiet', str(root)], check=True)
    (root / 'ntp').mkdir()
    (root / 'ntp' / 'tests').mkdir()
    (root / 'ntp' / 'hatch.toml').write_text(
        '[envs.default]\ne2e-env = false\n[[envs.default.matrix]]\npython = ["3.13"]\nversion = ["1", "2"]\n'
    )
    config_file.global_model.repos['core'] = str(root)
    config_file.save()

    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER), '--repo', 'DataDog/integrations-core', '--dry-run')

    assert result.exit_code == 0, result.output
    assert 'Batches -> 1 (2 jobs)' in result.output
    assert '\n    ntp\n' in result.output
    assert 'Planned batch batch-01 (2 jobs)' in result.output


def test_a_head_belonging_to_no_open_pull_request_dispatches_nothing(ddev, github, planned, tmp_path):
    """Nothing left to test resolves no run, so nothing identifies one on disk either."""
    github.mock_response('list_pull_requests', pulls_page())

    result = ddev('ci', 'dispatch-tests', *HEAD_LOOKUP_OPTIONS, '--output-dir', str(tmp_path))

    assert result.exit_code == 0, result.output
    assert 'No open pull request matches the requested revision' in result.output
    planned.assert_not_called()
    github.assert_not_called('create_workflow_dispatch')
    assert not (tmp_path / 'run.json').exists()


@pytest.mark.parametrize(
    'options',
    [HEAD_LOOKUP_OPTIONS, ('--pr', str(PR_NUMBER), '--pr-head-sha', HEAD_SHA)],
    ids=['lookup', 'explicit-pr'],
)
def test_a_head_that_moves_while_the_pull_request_is_read_dispatches_nothing(
    ddev, github, planned, options: tuple[str, ...]
):
    github.mock_response('list_pull_requests', pulls_page(listed_pull_request()))
    github.mock_response('get_pull_request', pull_request(head_sha='a-newer-sha'))

    result = ddev('ci', 'dispatch-tests', *options)

    assert result.exit_code == 0, result.output
    assert 'No open pull request matches the requested revision' in result.output
    planned.assert_not_called()
    github.assert_not_called('create_workflow_dispatch')


def test_a_head_heading_several_pull_requests_is_refused(
    ddev: CliRunner, github: FakeAsyncGitHubClient, planned: MagicMock
):
    github.mock_response(
        'list_pull_requests',
        pulls_page(listed_pull_request(number=1), listed_pull_request(number=2, base_branch='7.62.x')),
    )

    result = ddev('ci', 'dispatch-tests', *HEAD_LOOKUP_OPTIONS)

    assert result.exit_code == 1
    assert '2 open pull requests were found' in result.output
    assert HEAD_SHA in result.output
    assert 'https://github.com/DataDog/integrations-core/pull/1' in result.output
    assert 'https://github.com/DataDog/integrations-core/pull/2' in result.output
    assert 'A single open pull request is required to run tests.' in result.output
    planned.assert_not_called()
    github.assert_not_called('create_workflow_dispatch')


def test_a_base_branch_narrows_an_ambiguous_head(ddev, github, planned):
    github.mock_response(
        'list_pull_requests',
        pulls_page(listed_pull_request(number=1), listed_pull_request(number=2, base_branch='7.62.x')),
    )
    github.mock_response('get_pull_request', pull_request(number=2, base_branch='7.62.x'))

    result = ddev('ci', 'dispatch-tests', *HEAD_LOOKUP_OPTIONS, '--pr-base-branch', '7.62.x', '--dry-run')

    assert result.exit_code == 0, result.output
    assert github.last_call('get_pull_request').kwargs['pull_number'] == 2


@pytest.mark.parametrize(
    ('head_repo', 'base_branch'),
    [('DataDog/integrations-core', 'a-target-branch'), ('contributor/integrations-core', 'another-base')],
    ids=['same-repository', 'fork'],
)
def test_head_metadata_resolves_a_pull_request(
    ddev: CliRunner, github: FakeAsyncGitHubClient, planned: MagicMock, head_repo: str, base_branch: str
):
    github.mock_response(
        'list_pull_requests',
        pulls_page(listed_pull_request(head_repo=head_repo.upper(), base_branch=base_branch)),
        state='open',
        head=f'{head_repo.split("/")[0]}:hs/a-branch',
        base=None,
    )
    github.mock_response('get_pull_request', pull_request(head_repo=head_repo, base_branch=base_branch))

    result = ddev(
        'ci',
        'dispatch-tests',
        '--pr-head-sha',
        HEAD_SHA,
        '--pr-head-repo',
        head_repo,
        '--pr-head-branch',
        'hs/a-branch',
        '--dry-run',
    )

    assert result.exit_code == 0, result.output
    assert MERGE_SHA in result.output
    assert HEAD_SHA in result.output
    assert base_branch in result.output


def test_a_head_repository_that_changes_after_lookup_dispatches_nothing(
    ddev: CliRunner, github: FakeAsyncGitHubClient, planned: MagicMock
):
    github.mock_response('list_pull_requests', pulls_page(listed_pull_request()))
    github.mock_response('get_pull_request', pull_request(head_repo='DataDog/another-fork'))

    result = ddev('ci', 'dispatch-tests', *HEAD_LOOKUP_OPTIONS, '--dry-run')

    assert result.exit_code == 0, result.output
    assert 'No open pull request matches the requested revision' in result.output
    planned.assert_not_called()


@pytest.mark.parametrize(
    ('options', 'message'),
    [
        (['--pr-head-sha', HEAD_SHA], 'Specify `--pr` or all of'),
        (['--pr-head-sha', HEAD_SHA, '--pr-head-repo', 'DataDog/integrations-core'], 'Specify `--pr` or all of'),
        (['--pr-head-sha', HEAD_SHA, '--pr-head-branch', 'hs/a-branch'], 'Specify `--pr` or all of'),
        (
            ['--pr-head-repo', 'DataDog/integrations-core', '--pr-head-branch', 'hs/a-branch'],
            'Specify `--pr` or all of',
        ),
        (
            ['--pr-head-sha', HEAD_SHA, '--pr-head-repo', 'integrations-core', '--pr-head-branch', 'hs/a-branch'],
            'OWNER/NAME',
        ),
        (
            ['--pr-head-sha', HEAD_SHA, '--pr-head-repo', 'DataDog/integrations-core', '--pr-head-branch', ''],
            '`--pr-head-branch` must not be empty',
        ),
        (['--pr', str(PR_NUMBER), '--pr-head-sha', ''], '`--pr-head-sha` must not be empty'),
    ],
    ids=[
        'sha-only',
        'missing-branch',
        'missing-repository',
        'missing-sha',
        'invalid-repository',
        'empty-branch',
        'empty-sha',
    ],
)
def test_incomplete_head_identity_is_refused(
    ddev: CliRunner, github: FakeAsyncGitHubClient, planned: MagicMock, options: list[str], message: str
):
    result = ddev('ci', 'dispatch-tests', *options, '--dry-run')

    assert result.exit_code == 2
    assert message in result.output
    planned.assert_not_called()


def test_a_numbered_pull_request_must_match_its_base_constraint(ddev, github, planned):
    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER), '--pr-base-branch', 'another-base', '--dry-run')

    assert result.exit_code == 0, result.output
    assert 'No open pull request matches the requested revision' in result.output
    planned.assert_not_called()


def test_a_pull_request_that_is_no_longer_open_dispatches_nothing(ddev, github, planned):
    """Nothing to test at that point, and no open pull request to report to either."""
    github.mock_response('get_pull_request', pull_request(state=PullRequestState.CLOSED))

    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER))

    assert result.exit_code == 0, result.output
    assert 'No open pull request matches the requested revision' in result.output
    planned.assert_not_called()
    github.assert_not_called('create_workflow_dispatch')


def test_a_pull_request_without_a_merge_commit_is_retried_until_github_publishes_one(ddev, github, planned, mocker):
    """The SHA reads null only while GitHub computes the merge, so the run waits for it."""
    mocker.patch('ddev.cli.ci.dispatch_run.MERGE_COMMIT_REFRESH_SECONDS', 0.0)
    github.mock_response('get_pull_request', pull_request(merge_commit_sha=None), once=True)
    github.mock_response('get_pull_request', pull_request())

    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER), '--dry-run')

    assert result.exit_code == 0, result.output
    assert MERGE_SHA in result.output
    assert len(github.calls_to('get_pull_request')) == 2


def test_a_pull_request_whose_merge_commit_never_arrives_is_refused(ddev, fake_async_github, planned, mocker):
    mocker.patch('ddev.cli.ci.dispatch_run.MERGE_COMMIT_REFRESH_SECONDS', 0.0)
    fake_async_github.mock_response('get_pull_request', pull_request(merge_commit_sha=None))

    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER), '--dry-run')

    assert result.exit_code == 1
    assert 'reports no merge commit' in result.output
    planned.assert_not_called()


def test_a_pull_request_that_moves_while_its_merge_commit_is_awaited_is_refused(
    ddev, fake_async_github, planned, mocker
):
    """The re-read would otherwise hand the run a merge of a revision it never resolved."""
    mocker.patch('ddev.cli.ci.dispatch_run.MERGE_COMMIT_REFRESH_SECONDS', 0.0)
    fake_async_github.mock_response('get_pull_request', pull_request(merge_commit_sha=None), once=True)
    fake_async_github.mock_response('get_pull_request', pull_request(head_sha='a-newer-sha'), once=True)

    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER), '--dry-run')

    assert result.exit_code == 1
    assert 'changed while its merge commit was awaited' in result.output
    planned.assert_not_called()


@pytest.mark.parametrize(
    'pr_option',
    ['--pr', '--pr-head-sha', '--pr-head-repo', '--pr-head-branch', '--pr-base-branch'],
)
def test_commit_and_pr_options_cannot_be_combined(ddev, github, planned, pr_option: str):
    result = ddev('ci', 'dispatch-tests', '--commit', 'a-sha', pr_option, 'a-value', '--dry-run')

    assert result.exit_code == 2
    assert '`--commit` cannot be combined with PR options' in result.output
    planned.assert_not_called()


def test_a_run_that_dispatches_needs_a_token_before_it_plans(ddev, planned, mocker):
    """Planning shells out to git and Hatch for every target, so a missing token must stop it first."""
    mocker.patch.dict('os.environ', {'DD_GITHUB_TOKEN': '', 'GH_TOKEN': '', 'GITHUB_TOKEN': ''})

    result = ddev('ci', 'dispatch-tests', '--commit', 'a-sha')

    assert result.exit_code == 1
    assert 'A GitHub token is required' in result.output
    planned.assert_not_called()


def test_a_dry_run_of_a_commit_needs_no_token(ddev, planned, resolved_changes, mocker):
    """The only run that talks to nobody, since git answers the comparison."""
    mocker.patch.dict('os.environ', {'DD_GITHUB_TOKEN': '', 'GH_TOKEN': '', 'GITHUB_TOKEN': ''})

    result = ddev('ci', 'dispatch-tests', '--commit', 'a-sha', '--dry-run')

    assert result.exit_code == 0, result.output
    assert 'Dry run: nothing was dispatched' in result.output


def test_a_dry_run_of_a_pull_request_needs_a_token(ddev, planned, mocker):
    """Its merge commit comes from the API, so there is no offline version of the run."""
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


def test_a_reference_that_is_neither_a_number_nor_a_url_is_refused(ddev, github, planned):
    result = ddev('ci', 'dispatch-tests', '--pr', 'not-a-pull-request', '--dry-run')

    assert result.exit_code == 2
    assert 'neither a pull request number nor a pull request URL' in result.output
    planned.assert_not_called()


def test_an_empty_plan_is_not_dispatched(ddev, fake_async_github, resolved_changes, mocker):
    """Nothing to test is a clean outcome, not a failure and not an empty comment."""
    mocker.patch('ddev.cli.ci.dispatch_tests.build_plan', return_value=[])

    result = ddev('ci', 'dispatch-tests', '--commit', 'a-sha')

    assert result.exit_code == 0, result.output
    assert 'Nothing to test' in result.output
    fake_async_github.assert_not_called('create_workflow_dispatch')


def test_pytest_args_are_shown_in_the_plan(ddev, github, planned):
    """Catches an option click accepts but nothing forwards."""
    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER), '--pytest-args', '-m "not flaky"', '--dry-run')

    assert result.exit_code == 0, result.output
    assert '-m "not flaky"' in result.output


def test_invocation_options_reach_the_plan_and_batch_workflow(
    ddev: CliRunner,
    github: FakeAsyncGitHubClient,
    planned: MagicMock,
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    step_summary: Path,
):
    job = planned.return_value[0].job_list[0]
    mock_job_result(github, job, 'success')
    fast_dispatcher_config(mocker)
    monkeypatch.setattr('ddev.utils.github_async.AsyncGitHubClient', lambda token, rate_limiter=None, **kwargs: github)

    result = ddev(
        'ci',
        'dispatch-tests',
        '--pr',
        str(PR_NUMBER),
        '--workflow',
        'custom-batch.yml',
        '--workflow-ref',
        '7.62.x',
        '--tags',
        'team:platform',
        '--pytest-args',
        '-m "not flaky"',
        '--output-dir',
        str(tmp_path),
    )

    assert result.exit_code == 0, result.output
    assert 'custom-batch.yml @ 7.62.x' in result.output
    assert 'team:platform' in result.output
    assert '-m "not flaky"' in result.output
    [dispatch] = github.calls_to('create_workflow_dispatch')
    assert dispatch.kwargs['workflow_id'] == 'custom-batch.yml'
    assert dispatch.kwargs['ref'] == '7.62.x'
    inputs = dispatch.kwargs['inputs']
    assert inputs['pytest_args'] == '-m "not flaky"'
    [job_input] = decode_job_list(inputs['job_list'])
    assert 'team:agent-integrations' in job_input['additional_tags'].split(',')


@pytest.mark.parametrize(
    'mode_options',
    [[], ['--dry-run'], ['--resolve-only']],
    ids=['executing', 'dry-run', 'resolve-only'],
)
def test_metric_delivery_follows_the_dispatch_mode(
    ddev: CliRunner,
    github: FakeAsyncGitHubClient,
    mocker: MockerFixture,
    config_file: ConfigFileWithOverrides,
    mode_options: list[str],
):
    """A mode that dispatches nothing reports no metrics; an executing run delivers them."""
    config_file.model.orgs['default']['api_key'] = 'test-api-key'
    config_file.save()
    submitter = FakeMetricsSubmitter()
    mocker.patch(
        'ddev.monitoring.datadog_metrics.DatadogMetricsSink',
        partial(DatadogMetricsSink, submitter=submitter),
    )

    def resolve(*args: Any, monitor: ComponentMonitor, **kwargs: Any) -> ResolvedRun | None:
        monitor.metrics.count('probe')
        return resolve_run(*args, monitor=monitor, **kwargs)

    mocker.patch('ddev.cli.ci.dispatch_tests.resolve_run', resolve)
    mocker.patch('ddev.cli.ci.dispatch_tests.build_plan', return_value=[])

    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER), *mode_options)

    assert result.exit_code == 0, result.output
    if mode_options:
        assert submitter.series == []
        assert submitter.distributions == []
    else:
        assert {
            'agent_integrations.test_dispatcher.probe',
            'agent_integrations.test_dispatcher.runs.count',
        } <= {series['metric'] for series in submitter.series}
        assert [series['metric'] for series in submitter.distributions] == [
            'agent_integrations.test_dispatcher.run.duration'
        ]


def test_early_exit_disables_monitoring(
    ddev: CliRunner,
    github: FakeAsyncGitHubClient,
    planned: MagicMock,
    mocker: MockerFixture,
):
    github.mock_response('list_pull_requests', pulls_page())

    sink = RecordingSink()
    monitors: list[ComponentMonitor] = []

    def make_runtime(**kwargs: Any) -> MonitoringRuntime:
        kwargs['metrics_sink'] = sink
        runtime = MonitoringRuntime(**kwargs)
        monitor = runtime.component('dispatcher')
        monitor.metrics.count('before-exit')
        monitors.append(monitor)
        return runtime

    mocker.patch('ddev.monitoring.MonitoringRuntime', make_runtime)

    result = ddev('ci', 'dispatch-tests', *HEAD_LOOKUP_OPTIONS)

    assert result.exit_code == 0, result.output
    assert 'No open pull request matches the requested revision' in result.output
    [monitor] = monitors
    records_at_exit = list(sink.records)
    assert sink.records_named('before-exit')
    monitor.metrics.count('after-exit')
    assert sink.records == records_at_exit


def test_resolved_identity_reaches_planning_even_when_there_are_no_targets(
    ddev, fake_async_github, resolved_changes, mocker, tmp_path
):
    sink = RecordingSink()

    def make_runtime(**kwargs: Any) -> MonitoringRuntime:
        kwargs['metrics_sink'] = sink
        kwargs['metrics_tag_projector'] = projector_for('repo', 'head_sha', 'team', 'component')
        return MonitoringRuntime(**kwargs)

    def observe_plan(app: Application, *, monitor: ComponentMonitor, **kwargs: Any) -> list[TestBatch]:
        monitor.metrics.count('plan')
        return []

    mocker.patch('ddev.monitoring.MonitoringRuntime', make_runtime)
    mocker.patch('ddev.cli.ci.dispatch_tests.build_plan', observe_plan)

    result = ddev(
        'ci',
        'dispatch-tests',
        '--commit',
        'a-sha',
        '--tags',
        'repo:contributor/other head_sha:sneaky team:platform',
        '--output-dir',
        str(tmp_path),
    )

    assert result.exit_code == 0, result.output
    assert 'Nothing to test' in result.output
    # An empty plan is a valid outcome, so the run it belongs to is still identified on disk.
    assert (tmp_path / 'run.json').exists()
    [record] = sink.records_named('plan')
    assert record.tags == {
        'repo': 'DataDog/integrations-core',
        'head_sha': 'a-sha',
        'team': 'agent-integrations',
        'component': 'planner',
    }


@pytest.mark.parametrize(
    ('environ', 'pipeline_id'),
    [
        ({'GITHUB_RUN_ID': '111', 'GITHUB_RUN_ATTEMPT': '1'}, '111'),
        ({'GITHUB_RUN_ID': '111', 'GITHUB_RUN_ATTEMPT': '2'}, '111'),
        ({'GITHUB_RUN_ID': '222', 'GITHUB_RUN_ATTEMPT': '1'}, '222'),
        ({}, None),
    ],
    ids=['first-attempt', 'rerun', 'another-workflow', 'outside-github-actions'],
)
def test_metrics_are_tagged_with_the_workflow_running_the_dispatcher(
    ddev, fake_async_github, resolved_changes, mocker, monkeypatch, environ: dict[str, str], pipeline_id: str | None
):
    """A rerun reports as the same emitter, since it cannot run concurrently with the attempt it replaces."""
    for variable in ('GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT'):
        monkeypatch.delenv(variable, raising=False)
    for variable, value in environ.items():
        monkeypatch.setenv(variable, value)
    sink = recording_runtime(mocker)

    def observe_plan(app: Application, *, monitor: ComponentMonitor, **kwargs: Any) -> list[TestBatch]:
        monitor.metrics.count('plan')
        return []

    mocker.patch('ddev.cli.ci.dispatch_tests.build_plan', observe_plan)

    result = ddev('ci', 'dispatch-tests', '--commit', 'a-sha', '--tags', 'ci_pipeline_id:forged')

    assert result.exit_code == 0, result.output
    assert sink.records_named('plan')
    assert {record.tags.get('ci.pipeline.id') for record in sink.records} == {pipeline_id}


def test_pull_request_resolution_meters_the_rate_limit_wait_it_sits_out(ddev, resolved_changes, mocker, monkeypatch):
    """Resolution builds its own client before the Dispatcher's exists, so its waits need their own wiring."""
    clock = FakeClock()
    advance_clock_on_sleep(clock, monkeypatch)
    monkeypatch.setattr('ddev.utils.rate_limiting.monotonic', clock)
    monkeypatch.setattr('ddev.utils.github_async.defaults.BudgetGovernor', partial(BudgetGovernor, now=clock))
    responses = [
        httpx.Response(429, headers={'retry-after': '30'}),
        httpx.Response(200, json=pull_request().model_dump(mode='json')),
    ]
    transport = httpx.MockTransport(lambda request: responses.pop(0))
    mocker.patch('ddev.utils.github_async.async_github_client', partial(async_github_client, transport=transport))
    mocker.patch.dict('os.environ', {'DD_GITHUB_TOKEN': 'ghp_test'})
    mocker.patch('ddev.cli.ci.dispatch_tests.build_plan', return_value=[])
    monkeypatch.setenv('GITHUB_RUN_ID', '12345')
    handler = RecordingJsonHandler()
    sink = recording_runtime(mocker, handler)

    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER))

    assert result.exit_code == 0, result.output
    # The 30 seconds GitHub asked for, plus the governor's one-second buffer.
    assert [(record.value, dict(record.tags)) for record in sink.records_named('throttle.wait.duration')] == [
        (31, {'ci.pipeline.id': '12345', 'dispatcher.reason': 'secondary_limit', 'dispatcher.rate_limiter': 'github'})
    ]
    # Resolution's own requests are observed too, under the same pipeline ID.
    assert [
        (record.value, record.tags.get('ci.pipeline.id')) for record in sink.records_named('requests.throttled')
    ] == [
        (1, '12345'),
        (0, '12345'),
    ]
    assert [event['event'] for event in handler.events if event['level'] == 'warning'] == [
        'GitHub secondary rate limit hit: asked to retry after 30s, pausing all requests for 31s',
        'rate limit secondary pause: waiting 31.0s before the next request',
    ]


@pytest.mark.usefixtures('resolved_changes')
@pytest.mark.parametrize(
    ('level_options', 'visible', 'hidden'),
    [
        ((), ('planning batches', 'planning skipped a broken target'), ('planning detail',)),
        (('--log-level', 'Warning'), ('planning skipped a broken target',), ('planning detail', 'planning batches')),
    ],
    ids=['default-info', 'mixed-case-warning'],
)
def test_log_level_gates_console_and_datadog_output_together(
    ddev: CliRunner,
    mocker: MockerFixture,
    level_options: tuple[str, ...],
    visible: tuple[str, ...],
    hidden: tuple[str, ...],
):
    submitter = FakeLogSubmitter()

    def make_datadog_handler(app: Application, monitoring: MonitoringRuntime, *, level: int) -> DatadogLogHandler:
        datadog = DatadogLogHandler(api_key='test-api-key', submitter=submitter, level=level)
        datadog.setFormatter(dispatcher_datadog_formatter(ci={}))
        monitoring.add_log_handler(datadog)
        return datadog

    def observe_plan(app: Application, *, monitor: ComponentMonitor, **kwargs: Any) -> list[TestBatch]:
        monitor.logger.debug('planning detail')
        monitor.logger.info('planning batches')
        monitor.logger.warning('planning skipped a broken target')
        return []

    mocker.patch('ddev.cli.ci.dispatch_tests.attach_datadog_log_handler', make_datadog_handler)
    mocker.patch('ddev.cli.ci.dispatch_tests.build_plan', observe_plan)

    result = ddev('ci', 'dispatch-tests', '--commit', 'a-sha', '--dry-run', *level_options)

    assert result.exit_code == 0, result.output
    delivered = {log['message'] for log in submitter.logs}
    for message in visible:
        assert message in result.output
        assert message in delivered
    for message in hidden:
        assert message not in result.output
        assert message not in delivered


def test_log_level_is_bounded_to_a_known_severity(ddev: CliRunner):
    result = ddev('ci', 'dispatch-tests', '--commit', 'a-sha', '--dry-run', '--log-level', 'chatty')

    assert result.exit_code == 2
    assert "Invalid value for '--log-level'" in result.output


def test_attach_datadog_log_handler_delivers_at_the_requested_level(
    config_file: ConfigFileWithOverrides, mocker: MockerFixture
):
    config_file.model.orgs['default']['api_key'] = 'test-api-key'
    config_file.save()
    app = Application(lambda code: None, 0, False, False)
    app.config_file.path = config_file.path
    app.config_file.load()
    submitter = FakeLogSubmitter()
    mocker.patch('ddev.monitoring.datadog.DatadogLogHandler', partial(DatadogLogHandler, submitter=submitter))

    monitoring = MonitoringRuntime()
    handler = attach_datadog_log_handler(app, monitoring, level=logging.WARNING)
    assert handler is not None
    monitor = monitoring.component('dispatcher')
    monitor.logger.info('Polling workflow')
    monitor.logger.warning('Artifact download failed', run_id=123)

    monitoring.close()
    # The handler stays caller-owned, so the test drains it the way the entry point does.
    handler.close()

    [log] = submitter.logs
    assert log['message'] == 'Artifact download failed'
    assert log['status'] == 'warning'


def test_a_failing_datadog_metrics_constructor_leaves_the_dispatcher_usable(
    ddev: CliRunner,
    github: FakeAsyncGitHubClient,
    mocker: MockerFixture,
    config_file: ConfigFileWithOverrides,
):
    config_file.model.orgs['default']['api_key'] = 'test-api-key'
    config_file.save()
    mocker.patch('ddev.monitoring.datadog_metrics.DatadogMetricsSink', side_effect=RuntimeError('no client'))
    mocker.patch('ddev.cli.ci.dispatch_tests.build_plan', return_value=[])

    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER))

    assert result.exit_code == 0, result.output
    assert 'Datadog metric delivery is unavailable' in result.output
    assert 'RuntimeError: no client' in result.output
    assert 'Nothing to test' in result.output


def test_sink_failures_are_reported_through_the_dedicated_exporter_component(
    ddev: CliRunner,
    github: FakeAsyncGitHubClient,
    mocker: MockerFixture,
    config_file: ConfigFileWithOverrides,
):
    """One HTTP batch carries several components' metrics, so its failures are not any one of theirs."""
    config_file.model.orgs['default']['api_key'] = 'test-api-key'
    config_file.save()
    submitter = FakeMetricsSubmitter()
    submitter.fail_next(RuntimeError('intake unavailable'), count=100)
    mocker.patch(
        'ddev.monitoring.datadog_metrics.DatadogMetricsSink',
        partial(DatadogMetricsSink, submitter=submitter),
    )
    log_submitter = FakeLogSubmitter()

    def make_datadog_handler(app: Application, monitoring: MonitoringRuntime, *, level: int) -> DatadogLogHandler:
        datadog = DatadogLogHandler(api_key='test-api-key', submitter=log_submitter, level=level)
        datadog.setFormatter(dispatcher_datadog_formatter(ci={}))
        monitoring.add_log_handler(datadog)
        return datadog

    json_handler = RecordingJsonHandler()

    def make_runtime(**kwargs: Any) -> MonitoringRuntime:
        runtime = MonitoringRuntime(**kwargs)
        runtime.add_log_handler(json_handler)
        return runtime

    def observe_plan(app: Application, *, monitor: ComponentMonitor, **kwargs: Any) -> list[TestBatch]:
        monitor.metrics.count('planned')
        return []

    mocker.patch('ddev.cli.ci.dispatch_tests.attach_datadog_log_handler', make_datadog_handler)
    mocker.patch('ddev.monitoring.MonitoringRuntime', make_runtime)
    mocker.patch('ddev.cli.ci.dispatch_tests.build_plan', observe_plan)

    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER))

    assert result.exit_code == 0, result.output
    # The submission fails while the runtime drains the sink, and the report still reaches the
    # runtime's handlers before they detach.
    exporter_events = [event for event in json_handler.events if event.get('component') == 'datadog-metrics']
    assert exporter_events
    assert all(event['category'] == 'submission' for event in exporter_events)
    assert any(event['event'].startswith('submitting') for event in exporter_events)


def test_the_entry_point_drains_its_datadog_handler_before_the_command_returns(
    ddev: CliRunner,
    github: FakeAsyncGitHubClient,
    mocker: MockerFixture,
):
    """The attached Datadog handler is the entry point's own, not the runtime's: only the entry
    point's drain delivers what the run buffered, before the command returns."""

    class DeliversOnCloseHandler(RecordingJsonHandler):
        """A caller-owned handler whose buffered events only leave it through its own `close`."""

        def __init__(self) -> None:
            super().__init__()
            self.delivered: list[dict[str, Any]] = []

        def close(self, timeout: float = 10.0) -> None:
            self.delivered.extend(self.events)

    handler = DeliversOnCloseHandler()

    def make_datadog_handler(app: Application, monitoring: MonitoringRuntime, *, level: int) -> DeliversOnCloseHandler:
        handler.setLevel(level)
        monitoring.add_log_handler(handler)
        return handler

    mocker.patch('ddev.cli.ci.dispatch_tests.attach_datadog_log_handler', make_datadog_handler)

    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER), '--dry-run')

    assert result.exit_code == 0, result.output
    delivered = [event for event in handler.delivered if event.get('event') == 'Dispatcher invocation started']
    assert delivered, 'the run buffered a Dispatcher event the entry point never delivered'


def test_command_metrics_project_centralized_tags(
    ddev: CliRunner,
    github: FakeAsyncGitHubClient,
    mocker: MockerFixture,
    config_file: ConfigFileWithOverrides,
):
    config_file.model.orgs['default']['api_key'] = 'test-api-key'
    config_file.save()
    submitter = FakeMetricsSubmitter()
    mocker.patch(
        'ddev.monitoring.datadog_metrics.DatadogMetricsSink',
        partial(DatadogMetricsSink, submitter=submitter),
    )

    def observe_plan(app: Application, *, monitor: ComponentMonitor, **kwargs: Any) -> list[TestBatch]:
        monitor.metrics.count('planned', environment='py3.13', integration='ntp', blob='unselected')
        return []

    mocker.patch('ddev.cli.ci.dispatch_tests.build_plan', observe_plan)

    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER))

    assert result.exit_code == 0, result.output
    [series] = [item for item in submitter.series if item['metric'] == 'agent_integrations.test_dispatcher.planned']
    assert series['type'] == 1
    tags = series['tags']
    assert 'dispatcher.batch.job.environment:py3.13' in tags
    assert 'dispatcher.batch.job.integration:ntp' in tags
    assert 'git.repository.id_v2:github.com/datadog/integrations-core' in tags
    assert 'dispatcher.context:pr' in tags
    assert not any('pr.number' in tag for tag in tags)
    assert not any('blob' in tag for tag in tags)


def recording_runtime(mocker: MockerFixture, handler: logging.Handler | None = None) -> RecordingSink:
    """Deliver the command's metrics into a recording sink, under the production tag policy."""
    sink = RecordingSink()

    def make_runtime(**kwargs: Any) -> MonitoringRuntime:
        kwargs['metrics_sink'] = sink
        kwargs['metrics_tag_projector'] = metric_tag_mapping
        runtime = MonitoringRuntime(**kwargs)
        if handler is not None:
            runtime.add_log_handler(handler)
        return runtime

    mocker.patch('ddev.monitoring.MonitoringRuntime', make_runtime)
    return sink


def fast_dispatcher_config(mocker: MockerFixture) -> None:
    """Run the real bus without its production tail: the grace period is a wait for late messages."""
    config = DispatcherConfig(grace_period_seconds=0.1, global_timeout_seconds=5, poll_interval_seconds=0.01)
    mocker.patch.object(DispatcherConfig, 'from_repo_config', return_value=config)


@pytest.mark.parametrize('global_options', [(), ('-qq',)], ids=['normal', 'quiet'])
def test_an_executed_run_reports_its_execution_metrics(
    ddev: CliRunner,
    github: FakeAsyncGitHubClient,
    planned: MagicMock,
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    step_summary: Path,
    global_options: tuple[str, ...],
):
    job = planned.return_value[0].job_list[0]
    mock_job_result(github, job, 'success')
    sink = recording_runtime(mocker)
    fast_dispatcher_config(mocker)
    monkeypatch.setattr('ddev.utils.github_async.AsyncGitHubClient', lambda token, rate_limiter=None, **kwargs: github)

    result = ddev(*global_options, 'ci', 'dispatch-tests', '--pr', str(PR_NUMBER), '--output-dir', str(tmp_path))

    assert result.exit_code == 0, result.output
    cohort = Counter(record.name for record in sink.records if not record.name.startswith('operations.'))
    assert cohort == Counter(
        {
            'batches.count': 1,
            'batch.jobs.count': 1,
            'jobs.count': 1,
            'batch.duration': 1,
            'job.duration': 1,
            'artifacts.download.duration': 1,
            'runs.count': 1,
            'runs.failed': 1,
            'runs.planning_failed': 1,
            'runs.cancelled': 1,
            'runs.timed_out': 1,
            'runs.no_op': 1,
            'run.duration': 1,
            'jobs.incomplete': 1,
            'batches.failed': 1,
            'jobs.failed': 1,
            'jobs.skipped': 1,
        }
    )
    runs = sink.records_named('runs.count')[0]
    assert runs.tags['dispatcher.context'] == 'pr'
    assert runs.tags['git.repository.id_v2'] == 'github.com/datadog/integrations-core'
    assert runs.tags['dispatcher.component'] == 'dispatcher'
    # Run-level records carry no job dimensions: a mixed batch must not split them per integration.
    assert not any(tag.startswith('dispatcher.batch.job') for tag in runs.tags)
    counted = sink.records_named('jobs.count')[0]
    assert counted.tags['dispatcher.batch.job.integration'] == 'ntp'
    assert counted.tags['dispatcher.batch.job.environment'] == 'py3.13'
    operation_failures = {}
    for record in sink.records_named('operations.failed'):
        operation = record.tags['dispatcher.operation']
        operation_failures[operation] = operation_failures.get(operation, 0) + record.value
    assert operation_failures == {
        'dispatch_batch': 0,
        'fetch_workflow': 0,
        'refresh_jobs': 0,
        'collect_artifacts': 0,
        'gather_batch_results': 0,
        'publish_report': 0,
    }
    attempted = {record.tags['dispatcher.operation'] for record in sink.records_named('operations.count')}
    assert attempted == {
        'dispatch_batch',
        'fetch_workflow',
        'refresh_jobs',
        'collect_artifacts',
        'gather_batch_results',
        'publish_report',
    }


def test_a_failed_run_reports_failure_metrics_and_counts_itself_once(
    ddev: CliRunner,
    github: FakeAsyncGitHubClient,
    planned: MagicMock,
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    step_summary: Path,
):
    job = planned.return_value[0].job_list[0]
    mock_job_result(github, job, 'failure')
    github.mock_response(
        'get_workflow_run',
        make_workflow_run(name='test-batch', conclusion='failure'),
    )
    sink = recording_runtime(mocker)
    fast_dispatcher_config(mocker)
    monkeypatch.setattr('ddev.utils.github_async.AsyncGitHubClient', lambda token, rate_limiter=None, **kwargs: github)

    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER), '--output-dir', str(tmp_path))

    assert result.exit_code == 1, result.output
    assert 'Dispatcher tests failed.' in result.output
    assert [record.value for record in sink.records_named('runs.count')] == [1]
    assert [record.value for record in sink.records_named('runs.failed')] == [1]
    assert [record.value for record in sink.records_named('batches.failed')] == [1]
    failed = sink.records_named('jobs.failed')
    assert [record.value for record in failed] == [1]
    assert failed[0].tags['dispatcher.batch.job.integration'] == 'ntp'
    assert [record.value for record in sink.records_named('jobs.incomplete')] == [0]
    assert [record.value for record in sink.records_named('jobs.skipped')] == [0]


def test_a_run_whose_final_report_fails_is_counted_failed_without_invented_job_outcomes(
    ddev: CliRunner,
    github: FakeAsyncGitHubClient,
    planned: MagicMock,
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    step_summary: Path,
):
    job = planned.return_value[0].job_list[0]
    mock_job_result(github, job, 'success')
    for method in ('create_issue_comment', 'update_issue_comment', 'list_issue_comments'):
        github.mock_response(method, RuntimeError('the comment API is down'))
    sink = recording_runtime(mocker)
    fast_dispatcher_config(mocker)
    monkeypatch.setattr('ddev.utils.github_async.AsyncGitHubClient', lambda token, rate_limiter=None, **kwargs: github)

    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER), '--output-dir', str(tmp_path))

    assert result.exit_code == 1, result.output
    assert [record.value for record in sink.records_named('runs.count')] == [1]
    assert [record.value for record in sink.records_named('runs.failed')] == [1]
    assert [record.value for record in sink.records_named('batches.failed')] == [0]
    assert [record.value for record in sink.records_named('jobs.failed')] == [0]
    assert [record.value for record in sink.records_named('jobs.skipped')] == [0]
    assert [record.value for record in sink.records_named('jobs.incomplete')] == [0]


def test_a_planning_failure_is_reported_as_its_own_outcome(
    ddev: CliRunner, github: FakeAsyncGitHubClient, mocker: MockerFixture, tmp_path: Path
):
    handler = RecordingJsonHandler()
    sink = recording_runtime(mocker, handler=handler)
    mocker.patch('ddev.cli.ci.dispatch_tests.build_plan', side_effect=PlanningError('the plan is not valid'))

    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER), '--output-dir', str(tmp_path))

    assert result.exit_code == 1, result.output
    assert 'Could not build a test plan: the plan is not valid' in result.output
    assert [record.value for record in sink.records_named('runs.count')] == [1]
    assert [record.value for record in sink.records_named('runs.planning_failed')] == [1]
    assert [record.value for record in sink.records_named('runs.failed')] == [1]
    assert [record.value for record in sink.records_named('runs.no_op')] == [0]
    # No batch ran, so no batch outcome exists; there is no aggregate zero to invent.
    assert sink.records_named('batches.failed') == []
    assert not any(record.name.startswith('jobs.') for record in sink.records)
    [finished] = [event for event in handler.events if event['event'] == 'Dispatcher run finished']
    assert finished['outcome'] == 'planning-failed'
    assert finished['level'] == 'error'


@pytest.mark.parametrize(
    ('from_manifest', 'failure_point'),
    [
        (False, 'ddev.cli.ci.dispatch_tests.write_run_manifest'),
        (False, 'ddev.cli.ci.dispatch_tests.changes_for_run'),
        (False, 'ddev.cli.ci.tests.dispatcher_config.DispatcherConfig.from_repo_config'),
        (True, 'ddev.cli.ci.dispatch_tests.changes_for_run'),
        (True, 'ddev.cli.ci.tests.dispatcher_config.DispatcherConfig.from_repo_config'),
    ],
    ids=['manifest-write', 'resolved-changes', 'resolved-config', 'manifest-changes', 'manifest-config'],
)
def test_an_unexpected_failure_keeps_resolved_identity_and_still_propagates(
    ddev: CliRunner,
    github: FakeAsyncGitHubClient,
    mocker: MockerFixture,
    tmp_path: Path,
    from_manifest: bool,
    failure_point: str,
):
    handler = RecordingJsonHandler()
    sink = recording_runtime(mocker, handler=handler)
    options = ['--pr', str(PR_NUMBER)]
    if from_manifest:
        manifest = tmp_path / 'run.json'
        manifest.write_text(json.dumps(PULL_REQUEST_RUN_MANIFEST), encoding='utf-8')
        options = ['--run-manifest', str(manifest)]
    mocker.patch(failure_point, side_effect=OSError('setup failed'))

    with pytest.raises(OSError, match='setup failed'):
        ddev('ci', 'dispatch-tests', *options, '--output-dir', str(tmp_path))

    assert [record.value for record in sink.records_named('runs.count')] == [1]
    assert [record.value for record in sink.records_named('runs.cancelled')] == [0]
    [failed] = sink.records_named('runs.failed')
    assert failed.value == 1
    assert failed.tags['dispatcher.context'] == 'pr'
    assert failed.tags['git.branch'] == 'hs/a-branch'
    assert failed.tags['dispatcher.base_branch'] == 'a-target-branch'
    assert failed.tags['dispatcher.run.is_fork'] == 'false'
    assert failed.tags['team'] == 'agent-integrations'
    [finished] = [event for event in handler.events if event['event'] == 'Dispatcher run finished']
    assert finished['context'] == 'pr'
    assert finished['pr_number'] == PR_NUMBER
    assert finished['checkout_sha'] == MERGE_SHA
    assert finished['head_sha'] == HEAD_SHA
    assert finished['base_sha'] == BASE_SHA


def test_an_interrupt_during_resolution_is_counted_as_cancellation(
    ddev: CliRunner, github: FakeAsyncGitHubClient, mocker: MockerFixture, tmp_path: Path
):
    sink = recording_runtime(mocker)
    mocker.patch('ddev.cli.ci.dispatch_tests.changes_for_run', side_effect=KeyboardInterrupt)

    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER), '--output-dir', str(tmp_path))

    assert result.exit_code == 1
    assert [record.value for record in sink.records_named('runs.count')] == [1]
    assert [record.value for record in sink.records_named('runs.cancelled')] == [1]
    assert [record.value for record in sink.records_named('runs.failed')] == [0]


@pytest.mark.parametrize('from_manifest', [False, True], ids=['resolution', 'manifest'])
def test_a_resolution_failure_keeps_unresolved_metric_dimensions(
    ddev: CliRunner,
    fake_async_github: FakeAsyncGitHubClient,
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    from_manifest: bool,
):
    monkeypatch.setenv('GITHUB_RUN_ID', '12345')
    mocker.patch('ddev.cli.ci.dispatch_run.MERGE_COMMIT_REFRESH_SECONDS', 0.0)
    fake_async_github.mock_response('get_pull_request', pull_request(merge_commit_sha=None))
    handler = RecordingJsonHandler()
    sink = recording_runtime(mocker, handler=handler)
    options = ['--run-manifest', str(tmp_path / 'missing.json')] if from_manifest else ['--pr', str(PR_NUMBER)]

    result = ddev(
        'ci',
        'dispatch-tests',
        *options,
        '--output-dir',
        str(tmp_path),
        '--tags',
        'team:platform context:caller head_branch:caller base_branch:caller is_fork:false',
    )

    assert result.exit_code == 1, result.output
    assert ('Could not read run manifest' if from_manifest else 'reports no merge commit') in result.output
    assert [record.value for record in sink.records_named('runs.count')] == [1]
    assert [record.value for record in sink.records_named('runs.failed')] == [1]
    assert [record.value for record in sink.records_named('runs.no_op')] == [0]
    assert not any(record.name.startswith('jobs.') for record in sink.records)
    [failed] = sink.records_named('runs.failed')
    assert failed.tags == {
        'team': 'agent-integrations',
        'git.repository.id_v2': 'github.com/datadog/integrations-core',
        'dispatcher.context': 'unresolved',
        'git.branch': 'unresolved',
        'dispatcher.base_branch': 'unresolved',
        'dispatcher.run.is_fork': 'unresolved',
        'ci.pipeline.id': '12345',
        'dispatcher.component': 'dispatcher',
    }
    [started] = [event for event in handler.events if event['event'] == 'Dispatcher invocation started']
    assert started['team'] == 'agent-integrations'
    assert all(started[name] == 'unresolved' for name in ('context', 'head_branch', 'base_branch', 'is_fork'))


def test_a_superseded_revision_is_a_no_op_run_not_a_failure(
    ddev: CliRunner, github: FakeAsyncGitHubClient, planned: MagicMock, mocker: MockerFixture
):
    github.mock_response('list_pull_requests', pulls_page())
    sink = recording_runtime(mocker)

    result = ddev('ci', 'dispatch-tests', *HEAD_LOOKUP_OPTIONS)

    assert result.exit_code == 0, result.output
    assert 'No open pull request matches the requested revision' in result.output
    assert [record.value for record in sink.records_named('runs.count')] == [1]
    assert [record.value for record in sink.records_named('runs.no_op')] == [1]
    assert [record.value for record in sink.records_named('runs.failed')] == [0]
    assert not any(record.name.startswith('jobs.') for record in sink.records)


@pytest.mark.usefixtures('resolved_changes')
@pytest.mark.parametrize('global_options', [(), ('-qq',)], ids=['normal', 'quiet'])
def test_console_visibility_does_not_change_structured_events(
    ddev: CliRunner, mocker: MockerFixture, global_options: tuple[str, ...]
):
    json_handler = RecordingJsonHandler()

    def make_runtime(**kwargs: Any) -> MonitoringRuntime:
        runtime = MonitoringRuntime(**kwargs)
        runtime.add_log_handler(json_handler)
        return runtime

    def observe_plan(app: Application, *, monitor: ComponentMonitor, **kwargs: Any) -> list[TestBatch]:
        monitor.logger.info('planning batches')
        return []

    mocker.patch('ddev.monitoring.MonitoringRuntime', make_runtime)
    mocker.patch('ddev.cli.ci.dispatch_tests.build_plan', observe_plan)

    result = ddev(
        *global_options,
        'ci',
        'dispatch-tests',
        '--commit',
        'a-sha',
        '--dry-run',
        '--tags',
        'repo:contributor/other head_sha:sneaky team:platform',
    )

    assert result.exit_code == 0, result.output
    assert ('planning batches' in result.output) == (not global_options)
    assert 'repo=' not in result.output
    assert 'head_sha=' not in result.output
    assert 'team=' not in result.output
    [event] = [item for item in json_handler.events if item['event'] == 'planning batches']
    assert event['repo'] == 'DataDog/integrations-core'
    assert event['head_sha'] == 'a-sha'
    assert event['team'] == 'agent-integrations'
    assert event['component'] == 'planner'
    [finished] = [item for item in json_handler.events if item['event'] == 'Dispatcher run finished']
    assert finished['outcome'] == 'no-op'
    assert finished['cancelled'] is False


@pytest.mark.usefixtures('resolved_changes')
def test_console_lines_show_operational_context_without_large_payloads(ddev: CliRunner, mocker: MockerFixture):
    """A console line stays readable on its operational context; the payload behind it stays in
    the structured event."""
    json_handler = RecordingJsonHandler()

    def make_runtime(**kwargs: Any) -> MonitoringRuntime:
        runtime = MonitoringRuntime(**kwargs)
        runtime.add_log_handler(json_handler)
        return runtime

    def observe_plan(app: Application, *, monitor: ComponentMonitor, **kwargs: Any) -> list[TestBatch]:
        monitor.logger.info(
            'Batch batch-01 dispatched as workflow run 123',
            batch_id='batch-01',
            run_id=123,
            batch_state='queued',
            batch_job_count=2,
            batch_integration_count=2,
            batch_integrations=['ntp', 'redis'],
            workflow_url='https://github.com/DataDog/integrations-core/actions/runs/123',
            artifact_id=456,
            artifact_name='unit-ntp-py3.13-linux',
            path='/tmp/artifacts/unit-ntp-py3.13-linux',
        )
        return []

    mocker.patch('ddev.monitoring.MonitoringRuntime', make_runtime)
    mocker.patch('ddev.cli.ci.dispatch_tests.build_plan', observe_plan)

    result = ddev('ci', 'dispatch-tests', '--commit', 'a-sha', '--dry-run')

    assert result.exit_code == 0, result.output
    line = next(line for line in result.output.splitlines() if 'dispatched as workflow run 123' in line)
    assert 'component=planner' in line
    assert 'batch_id=batch-01' in line
    assert 'run_id=123' in line
    assert 'batch_state=queued' in line
    assert 'batch_job_count=2' in line
    assert 'batch_integration_count=2' in line
    assert 'batch_integrations' not in line
    assert 'https://' not in line
    assert 'unit-ntp-py3.13-linux' not in line

    [event] = [item for item in json_handler.events if item['event'] == 'Batch batch-01 dispatched as workflow run 123']
    assert event['batch_integrations'] == ['ntp', 'redis']
    assert event['workflow_url'] == 'https://github.com/DataDog/integrations-core/actions/runs/123'
    assert event['artifact_id'] == 456


PULL_REQUEST_RUN_MANIFEST = {
    'schema_version': 2,
    'repository': 'DataDog/integrations-core',
    'checkout_sha': MERGE_SHA,
    'head_sha': HEAD_SHA,
    'head_branch': 'hs/a-branch',
    'all_targets': False,
    'pr_number': PR_NUMBER,
    'base_branch': 'a-target-branch',
    'base_sha': BASE_SHA,
    'is_fork': False,
}

COMMIT_RUN_MANIFEST = {
    **PULL_REQUEST_RUN_MANIFEST,
    'checkout_sha': 'a-sha',
    'head_sha': 'a-sha',
    'head_branch': 'a-branch',
    'pr_number': None,
    'base_branch': None,
    'base_sha': None,
}


def merge_checkout(mocker, head: str = MERGE_SHA, parents: dict[str, str] | None = None) -> MagicMock:
    """A checkout claiming to be the recorded merge; a parent it lacks fails like a shallow fetch."""
    mocker.patch('ddev.utils.git.GitRepository.latest_commit', return_value=GitCommit(head))
    answers = PARENTS if parents is None else parents

    def rev_parse(*args: str) -> str:
        if args[-1] not in answers:
            raise OSError('fatal: bad revision')
        return answers[args[-1]]

    return mocker.patch('ddev.utils.git.GitRepository.capture', side_effect=rev_parse)


@pytest.mark.parametrize(
    ('options', 'pr_head_repo', 'expected'),
    [
        pytest.param(['--commit', 'a-sha'], None, COMMIT_RUN_MANIFEST, id='commit'),
        pytest.param(
            ['--pr', str(PR_NUMBER)],
            'contributor/integrations-core',
            {**PULL_REQUEST_RUN_MANIFEST, 'is_fork': True},
            id='fork-pull-request',
        ),
    ],
)
def test_a_resolved_run_writes_its_manifest(ddev, github, planned, mocker, tmp_path, options, pr_head_repo, expected):
    """The output directory records which run owns it, before any plan decides what to dispatch.

    The ordinary pull-request shape is asserted by the round-trip test; the fork stays because the
    manifest is what tells phase two to withhold same-repository credentials.
    """
    # A commit run reports whichever branch its repository has checked out, which no test controls.
    mocker.patch('ddev.utils.git.GitRepository.current_branch', return_value='a-branch')
    if pr_head_repo is not None:
        github.mock_response('get_pull_request', pull_request(head_repo=pr_head_repo))

    result = ddev('ci', 'dispatch-tests', *options, '--dry-run', '--output-dir', str(tmp_path))

    assert result.exit_code == 0, result.output
    content = (tmp_path / 'run.json').read_text(encoding='utf-8')
    assert content.endswith('}\n')
    assert json.loads(content) == expected


def test_without_an_output_directory_the_manifest_uses_the_dispatcher_default(ddev, github, planned, local_repo):
    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER), '--dry-run')

    assert result.exit_code == 0, result.output
    manifest = json.loads((local_repo / '.dispatcher' / 'run.json').read_text(encoding='utf-8'))
    assert manifest['pr_number'] == PR_NUMBER


def test_a_pull_request_round_trips_through_its_manifest(
    ddev, fake_async_github, planned, local_changes, mocker, tmp_path
):
    """Phase one resolves and records; phase two validates the checkout against the manifest,
    computes the changes from the merge commit itself, and plans them without resolving the
    pull request again.
    """
    fake_async_github.mock_response('get_pull_request', pull_request())
    planning_config = mocker.patch('ddev.cli.ci.tests.dispatcher_config.DispatcherConfig.from_repo_config')

    first = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER), '--resolve-only', '--output-dir', str(tmp_path))

    assert first.exit_code == 0, first.output
    planned.assert_not_called()
    planning_config.assert_not_called()
    assert json.loads((tmp_path / 'run.json').read_text(encoding='utf-8')) == PULL_REQUEST_RUN_MANIFEST

    merge_checkout(mocker)
    github_calls = len(fake_async_github.requests)
    second = ddev('ci', 'dispatch-tests', '--run-manifest', str(tmp_path / 'run.json'), '--dry-run')

    assert second.exit_code == 0, second.output
    assert len(fake_async_github.requests) == github_calls
    local_changes.assert_called_once_with(ANY, MERGE_SHA)
    assert planned.call_args.kwargs['changed_files'] == local_changes.return_value


@pytest.mark.parametrize(
    ('checked_out', 'parents', 'message'),
    [
        (HEAD_SHA, PARENTS, 'The checkout is'),
        (MERGE_SHA, {f'{MERGE_SHA}^2': BASE_SHA}, 'carries PR head'),
        (MERGE_SHA, {}, 'is not a merge commit this repository holds'),
    ],
)
def test_a_manifest_the_checkout_does_not_match_is_refused_before_planning(
    ddev, planned, tmp_path, mocker, checked_out, parents, message
):
    """Phase two refuses a different tree or a merge built from a different PR head."""
    merge_checkout(mocker, checked_out, parents)
    (tmp_path / 'run.json').write_text(json.dumps(PULL_REQUEST_RUN_MANIFEST), encoding='utf-8')

    result = ddev('ci', 'dispatch-tests', '--run-manifest', str(tmp_path / 'run.json'), '--dry-run')

    assert result.exit_code == 1
    assert message in result.output
    planned.assert_not_called()


def test_an_all_target_run_round_trips_through_its_recorded_scope(
    ddev, fake_async_github, planned, local_changes, mocker, tmp_path
):
    """`--all` skips the comparison, not the checkout: the plan still reads the checked-out tree."""
    fake_async_github.mock_response('get_pull_request', pull_request())

    first = ddev(
        'ci', 'dispatch-tests', '--pr', str(PR_NUMBER), '--all', '--resolve-only', '--output-dir', str(tmp_path)
    )

    assert first.exit_code == 0, first.output
    assert json.loads((tmp_path / 'run.json').read_text(encoding='utf-8')) == {
        **PULL_REQUEST_RUN_MANIFEST,
        'all_targets': True,
    }

    checkout = merge_checkout(mocker)
    second = ddev('ci', 'dispatch-tests', '--run-manifest', str(tmp_path / 'run.json'), '--dry-run')

    assert second.exit_code == 0, second.output
    checkout.assert_called()
    local_changes.assert_not_called()
    assert planned.call_args.kwargs['changed_files'] is None


@pytest.mark.parametrize(
    ('content', 'message'),
    [
        pytest.param(None, 'Could not read run manifest', id='missing-file'),
        pytest.param('{not json', 'is not a valid run', id='malformed-json'),
        pytest.param(b'\xff', 'is not a valid run', id='invalid-utf8'),
        pytest.param(
            json.dumps({**PULL_REQUEST_RUN_MANIFEST, 'schema_version': 3}),
            'is not a valid run',
            id='newer-schema',
        ),
        pytest.param(
            json.dumps({**PULL_REQUEST_RUN_MANIFEST, 'repository': 'DataDog/integrations-extras'}),
            'describes repository',
            id='other-repository',
        ),
    ],
)
def test_an_unusable_manifest_is_refused(ddev, planned, tmp_path, content: str | bytes | None, message: str):
    """Whatever is wrong with the file, planning never starts from a run that could not be read."""
    if isinstance(content, bytes):
        (tmp_path / 'run.json').write_bytes(content)
    elif content is not None:
        (tmp_path / 'run.json').write_text(content, encoding='utf-8')

    result = ddev('ci', 'dispatch-tests', '--run-manifest', str(tmp_path / 'run.json'), '--dry-run')

    assert result.exit_code == 1
    assert message in result.output
    planned.assert_not_called()


@pytest.mark.parametrize(
    'option', ['--pr', '--commit', '--all', '--pr-head-sha', '--pr-head-repo', '--pr-head-branch', '--pr-base-branch']
)
def test_a_manifest_cannot_also_select_the_run(ddev, github, planned, option: str):
    """The manifest decides the run; also passing a selection option would leave the choice ambiguous."""
    value = [] if option == '--all' else ['a-value']
    result = ddev('ci', 'dispatch-tests', '--run-manifest', 'a-manifest.json', option, *value, '--dry-run')

    assert result.exit_code == 2
    assert f'`--run-manifest` supplies the resolved run, so it cannot be combined with `{option}`' in result.output
    planned.assert_not_called()


def test_resolve_only_cannot_reuse_a_manifest(ddev, planned):
    result = ddev('ci', 'dispatch-tests', '--resolve-only', '--run-manifest', 'a-manifest.json')

    assert result.exit_code == 2
    assert '`--resolve-only` and `--run-manifest` cannot be combined.' in result.output
    planned.assert_not_called()


def test_resolve_only_warns_when_dry_run_is_redundant(ddev, planned, tmp_path):
    result = ddev(
        'ci',
        'dispatch-tests',
        '--resolve-only',
        '--dry-run',
        '--commit',
        'a-sha',
        '--output-dir',
        str(tmp_path),
    )

    assert result.exit_code == 0, result.output
    assert '`--dry-run` has no effect with `--resolve-only`.' in result.output
    assert (tmp_path / 'run.json').exists()
    planned.assert_not_called()
