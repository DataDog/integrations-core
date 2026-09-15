# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for `ddev ci dispatch-tests`: how it resolves the run it is asked to test."""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING, Any
from unittest.mock import ANY

import pytest

from ddev.monitoring import MonitoringRuntime
from ddev.utils.git import ChangedFile, ChangeType, GitCommit
from ddev.utils.github_async.models import PullRequest
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
    '--pr-head-branch',
    'hs/a-branch',
)

MERGE_SHA = 'merge-sha-mmm'
BASE_SHA = 'base-sha-bbb'
# GitHub's base snapshot may lag the first parent used for the synthetic merge.
PARENTS = {f'{MERGE_SHA}^1': 'current-master-sha-ccc', f'{MERGE_SHA}^2': HEAD_SHA}


def pull_request(
    state: str = 'open',
    number: int = PR_NUMBER,
    head_sha: str = HEAD_SHA,
    base_branch: str = 'a-target-branch',
    base_sha: str = BASE_SHA,
    head_repo: str | None = 'DataDog/integrations-core',
    merge_commit_sha: str | None = MERGE_SHA,
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
        base={'ref': base_branch, 'sha': base_sha},
        changed_files=1,
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
    github.mock_response('get_pull_request', pull_request(state='closed'))

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
    assert 'Dry run: nothing was dispatched.' in result.output


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
    assert 'No affected target to test.' in result.output
    fake_async_github.assert_not_called('create_workflow_dispatch')


def test_pytest_args_are_shown_in_the_plan(ddev, github, planned):
    """Catches an option click accepts but nothing forwards."""
    result = ddev('ci', 'dispatch-tests', '--pr', str(PR_NUMBER), '--pytest-args', '-m "not flaky"', '--dry-run')

    assert result.exit_code == 0, result.output
    assert '-m "not flaky"' in result.output


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


def test_resolved_identity_reaches_planning_even_when_there_are_no_targets(ddev, resolved_changes, mocker, tmp_path):
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
        'repo:contributor/other head_sha:sneaky team:platform',
        '--output-dir',
        str(tmp_path),
    )

    assert result.exit_code == 0, result.output
    assert 'No affected target to test.' in result.output
    # An empty plan is a valid outcome, so the run it belongs to is still identified on disk.
    assert (tmp_path / 'run.json').exists()
    [record] = sink.records
    assert record.fields['repo'] == 'DataDog/integrations-core'
    assert record.fields['head_sha'] == 'a-sha'
    assert record.fields['team'] == 'platform'
    assert record.fields['component'] == 'planner'


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
    [event] = json_handler.events
    assert event['repo'] == 'DataDog/integrations-core'
    assert event['head_sha'] == 'a-sha'
    assert event['team'] == 'platform'
    assert event['component'] == 'planner'
    assert event['event'] == 'planning batches'


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
