# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for `ddev ci dispatch-tests`: how it resolves the run it is asked to test."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING, Any

import pytest

from ddev.monitoring import MonitoringRuntime
from ddev.utils.github_async import GitHubResponse
from ddev.utils.github_async.models import PullRequest, PullRequestFile
from tests.cli.ci.helpers import HEAD_SHA, PR_NUMBER, listed_pull_request, pulls_page
from tests.cli.ci.tests.helpers import make_batch, make_job
from tests.helpers.monitoring import RecordingJsonHandler, RecordingSink

if TYPE_CHECKING:
    from pathlib import Path
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture

    from ddev.cli.application import Application
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
    '--pr-head-ref',
    'hs/a-branch',
)


def pull_request(
    state: str = 'open',
    changed_files: int = 1,
    number: int = PR_NUMBER,
    head_sha: str = HEAD_SHA,
    base_ref: str = 'a-target-branch',
    head_repo: str | None = 'DataDog/integrations-core',
) -> PullRequest:
    return PullRequest(
        number=number,
        html_url=f'https://github.com/DataDog/integrations-core/pull/{number}',
        state=state,
        head={
            'ref': 'hs/a-branch',
            'sha': head_sha,
            'repo': {'full_name': head_repo} if head_repo is not None else None,
        },
        base={'ref': base_ref, 'sha': 'base-sha-bbb'},
        changed_files=changed_files,
    )


def files_page(*files: PullRequestFile) -> GitHubResponse[list[PullRequestFile]]:
    return GitHubResponse[list[PullRequestFile]].model_validate({'data': list(files), 'headers': {}})


@pytest.fixture
def planned(mocker):
    """Keep PR-resolution tests independent of the planning layer."""
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
    'options',
    [
        ['--pr', str(PR_NUMBER)],
        ['--pr', f'https://github.com/DataDog/integrations-core/pull/{PR_NUMBER}'],
        ['--pr', str(PR_NUMBER), '--pr-head-sha', HEAD_SHA],
        ['--pr', str(PR_NUMBER), '--pr-head-ref', 'hs/a-branch'],
        ['--pr', str(PR_NUMBER), '--pr-base-ref', 'a-target-branch'],
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
    # A pull request is tested at its merge commit, not at its head.
    assert f'refs/pull/{PR_NUMBER}/merge' in result.output


def test_dispatch_tests_plans_from_hatch_toml(
    ddev: CliRunner, github: FakeAsyncGitHubClient, config_file: ConfigFileWithOverrides, tmp_path: Path
):
    root = tmp_path / 'repo'
    (root / '.ddev').mkdir(parents=True)
    (root / '.ddev' / 'config.toml').write_text('')
    subprocess.run(['git', 'init', '--quiet', str(root)], check=True)
    (root / 'ntp').mkdir()
    (root / 'ntp' / 'hatch.toml').write_text(
        '[envs.default]\ne2e-env = false\n[[envs.default.matrix]]\npython = ["3.13"]\nversion = ["1", "2"]\n'
    )
    config_file.global_model.repos['core'] = str(root)
    config_file.save()

    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER), '--repo', 'DataDog/integrations-core', '--dry-run')

    assert result.exit_code == 0, result.output
    assert 'Batches -> 1 (2 jobs)' in result.output
    assert '\n    ntp\n' in result.output


def test_a_head_belonging_to_no_open_pull_request_dispatches_nothing(ddev, github, planned):
    github.mock_response('list_pull_requests', pulls_page())

    result = ddev('ci', 'dispatch-tests', *HEAD_LOOKUP_OPTIONS)

    assert result.exit_code == 0, result.output
    assert 'No open pull request matches the requested revision' in result.output
    planned.assert_not_called()
    github.assert_not_called('create_workflow_dispatch')


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
        pulls_page(listed_pull_request(number=1), listed_pull_request(number=2, base_ref='7.62.x')),
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


def test_a_base_ref_narrows_an_ambiguous_head(ddev, github, planned):
    github.mock_response(
        'list_pull_requests',
        pulls_page(listed_pull_request(number=1), listed_pull_request(number=2, base_ref='7.62.x')),
    )
    github.mock_response('get_pull_request', pull_request(number=2, base_ref='7.62.x'))

    result = ddev('ci', 'dispatch-tests', *HEAD_LOOKUP_OPTIONS, '--pr-base-ref', '7.62.x', '--dry-run')

    assert result.exit_code == 0, result.output
    assert github.last_call('get_pull_request').kwargs['pull_number'] == 2


@pytest.mark.parametrize(
    ('head_repo', 'base_ref'),
    [('DataDog/integrations-core', 'a-target-branch'), ('contributor/integrations-core', 'another-base')],
    ids=['same-repository', 'fork'],
)
def test_head_metadata_resolves_a_pull_request(
    ddev: CliRunner, github: FakeAsyncGitHubClient, planned: MagicMock, head_repo: str, base_ref: str
):
    github.mock_response(
        'list_pull_requests',
        pulls_page(listed_pull_request(head_repo=head_repo.upper(), base_ref=base_ref)),
        state='open',
        head=f'{head_repo.split("/")[0]}:hs/a-branch',
        base=None,
    )
    github.mock_response('get_pull_request', pull_request(head_repo=head_repo, base_ref=base_ref))

    result = ddev(
        'ci',
        'dispatch-tests',
        '--pr-head-sha',
        HEAD_SHA,
        '--pr-head-repo',
        head_repo,
        '--pr-head-ref',
        'hs/a-branch',
        '--dry-run',
    )

    assert result.exit_code == 0, result.output
    assert f'refs/pull/{PR_NUMBER}/merge' in result.output
    assert HEAD_SHA in result.output
    assert base_ref in result.output


def test_a_head_repository_that_changes_after_lookup_dispatches_nothing(
    ddev: CliRunner, github: FakeAsyncGitHubClient, planned: MagicMock
):
    github.mock_response('list_pull_requests', pulls_page(listed_pull_request()))
    github.mock_response('get_pull_request', pull_request(head_repo='DataDog/another-fork'))

    result = ddev('ci', 'dispatch-tests', *HEAD_LOOKUP_OPTIONS, '--dry-run')

    assert result.exit_code == 0, result.output
    assert 'No open pull request matches the requested revision' in result.output
    github.assert_not_called('list_pull_request_files')
    planned.assert_not_called()


@pytest.mark.parametrize(
    ('options', 'message'),
    [
        (['--pr-head-sha', HEAD_SHA], 'Specify `--pr` or all of'),
        (['--pr-head-sha', HEAD_SHA, '--pr-head-repo', 'DataDog/integrations-core'], 'Specify `--pr` or all of'),
        (['--pr-head-sha', HEAD_SHA, '--pr-head-ref', 'hs/a-branch'], 'Specify `--pr` or all of'),
        (
            ['--pr-head-repo', 'DataDog/integrations-core', '--pr-head-ref', 'hs/a-branch'],
            'Specify `--pr` or all of',
        ),
        (
            ['--pr-head-sha', HEAD_SHA, '--pr-head-repo', 'integrations-core', '--pr-head-ref', 'hs/a-branch'],
            'OWNER/NAME',
        ),
        (
            ['--pr-head-sha', HEAD_SHA, '--pr-head-repo', 'DataDog/integrations-core', '--pr-head-ref', ''],
            '`--pr-head-ref` must not be empty',
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
    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER), '--pr-base-ref', 'another-base', '--dry-run')

    assert result.exit_code == 0, result.output
    assert 'No open pull request matches the requested revision' in result.output
    planned.assert_not_called()


def test_a_pull_request_that_is_no_longer_open_dispatches_nothing(ddev, github, planned):
    """Nothing to test at that point, and no open pull request to report to either."""
    github.mock_response('get_pull_request', pull_request(state='closed'))

    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER))

    assert result.exit_code == 0, result.output
    assert 'No open pull request matches the requested revision' in result.output
    planned.assert_not_called()
    github.assert_not_called('create_workflow_dispatch')


def test_an_incomplete_diff_aborts_rather_than_testing_part_of_the_change(ddev, github, planned):
    """The files endpoint truncates silently, so a count that disagrees has to stop the run."""
    github.mock_response('get_pull_request', pull_request(changed_files=97))

    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER), '--dry-run')

    assert result.exit_code == 1
    assert 'reports 97 changed files but the API listed 1' in result.output
    planned.assert_not_called()


def test_a_pull_request_that_changes_no_file_dispatches_nothing(ddev, github, planned):
    """Listing the files of an empty diff would meet a count of 0 and read that as truncation."""
    github.mock_response('get_pull_request', pull_request(changed_files=0))

    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER))

    assert result.exit_code == 0, result.output
    assert 'changes no file' in result.output
    github.assert_not_called('list_pull_request_files')
    planned.assert_not_called()
    github.assert_not_called('create_workflow_dispatch')


@pytest.mark.parametrize(
    'pr_option',
    ['--pr', '--pr-head-sha', '--pr-head-repo', '--pr-head-ref', '--pr-base-ref'],
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


def test_a_reference_that_is_neither_a_number_nor_a_url_is_refused(ddev, github, planned):
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


def test_pytest_args_are_shown_in_the_plan(ddev, github, planned):
    """Catches an option click accepts but nothing forwards."""
    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER), '--pytest-args', '-m "not flaky"', '--dry-run')

    assert result.exit_code == 0, result.output
    assert '-m "not flaky"' in result.output


def test_all_targets_plans_without_reading_a_diff(ddev, github, planned):
    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER), '--all', '--dry-run')

    assert result.exit_code == 0, result.output
    github.assert_not_called('list_pull_request_files')
    assert planned.call_args.kwargs['changed_files'] is None


@pytest.mark.parametrize(
    ('extra_options', 'asserted_output'),
    [
        (['--dry-run'], 'Dry run: nothing was dispatched.'),
        ([*HEAD_LOOKUP_OPTIONS], 'No open pull request matches the requested revision'),
    ],
    ids=['dry-run', 'no-open-pull-request'],
)
def test_early_exit_disables_monitoring(
    ddev: CliRunner,
    github: FakeAsyncGitHubClient,
    planned: MagicMock,
    mocker: MockerFixture,
    extra_options: list[str],
    asserted_output: str,
):
    if [*HEAD_LOOKUP_OPTIONS] == extra_options:
        github.mock_response('list_pull_requests', pulls_page())

    sink = RecordingSink()
    monitors: list[ComponentMonitor] = []

    def make_runtime(**kwargs: Any) -> MonitoringRuntime:
        runtime = MonitoringRuntime(metrics_sink=sink, **kwargs)
        monitor = runtime.component('dispatcher')
        monitor.metrics.count('before-exit')
        monitors.append(monitor)
        return runtime

    mocker.patch('ddev.monitoring.MonitoringRuntime', make_runtime)

    result = ddev('ci', 'dispatch-tests', *extra_options)

    assert result.exit_code == 0, result.output
    assert asserted_output in result.output
    [monitor] = monitors
    monitor.metrics.count('after-exit')
    assert [record.name for record in sink.records] == ['before-exit']


def test_resolved_identity_reaches_planning_even_when_there_are_no_targets(ddev, local_changes, mocker):
    sink = RecordingSink()

    def make_runtime(**kwargs: Any) -> MonitoringRuntime:
        return MonitoringRuntime(metrics_sink=sink, **kwargs)

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
        '--dry-run',
        '--tags',
        'repo:contributor/other commit:sneaky team:platform',
    )

    assert result.exit_code == 0, result.output
    assert 'No affected target to test.' in result.output
    [record] = sink.records
    assert record.fields['repo'] == 'DataDog/integrations-core'
    assert record.fields['commit'] == 'a-sha'
    assert record.fields['team'] == 'platform'
    assert record.fields['component'] == 'planner'


@pytest.mark.usefixtures('local_changes')
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
        'repo:contributor/other commit:sneaky team:platform',
    )

    assert result.exit_code == 0, result.output
    assert ('planning batches' in result.output) == (not global_options)
    assert 'repo=' not in result.output
    assert 'commit=' not in result.output
    assert 'team=' not in result.output
    [event] = json_handler.events
    assert event['repo'] == 'DataDog/integrations-core'
    assert event['commit'] == 'a-sha'
    assert event['team'] == 'platform'
    assert event['component'] == 'planner'
    assert event['event'] == 'planning batches'
