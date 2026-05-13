# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from unittest.mock import MagicMock, call

import pytest
from pytest_mock import MockerFixture

from ddev.cli.release.port_commit_workflow import (
    CherryPickStep,
    CommitStep,
    CreatePullRequestStep,
    PortStep,
    PortStepError,
    PreserveInTotoStep,
    build_pr_body,
    parse_labels,
    split_commit_subject,
)
from ddev.utils.git import GitCommit
from ddev.utils.github_async.models import PullRequest
from tests.helpers.github_async import FakeAsyncGitHubClient
from tests.helpers.runner import CliRunner


@pytest.fixture
def app_mock(mocker: MockerFixture) -> MagicMock:
    app = mocker.MagicMock()
    app.status.return_value.__enter__ = MagicMock(return_value=None)
    app.status.return_value.__exit__ = MagicMock(return_value=None)
    return app


@pytest.mark.parametrize(
    'subject,expected_clean,expected_pr',
    [
        ('Fix flake (#12345)', 'Fix flake', '12345'),
        ('Fix flake', 'Fix flake', None),
        ('Multi part subject (#1)', 'Multi part subject', '1'),
        ('Trailing spaces (#999)   ', 'Trailing spaces', '999'),
    ],
)
def test_split_commit_subject(subject, expected_clean, expected_pr):
    assert split_commit_subject(subject) == (expected_clean, expected_pr)


@pytest.mark.parametrize(
    'raw,expected',
    [
        ('qa/skip-qa', ['qa/skip-qa']),
        ('qa/skip-qa, backport/7.62.x', ['qa/skip-qa', 'backport/7.62.x']),
        ('', []),
        ('  ,  , ', []),
    ],
)
def test_parse_labels(raw, expected):
    assert parse_labels(raw) == expected


def test_build_pr_body_uses_template(app_mock, tmp_path):
    template_dir = tmp_path / '.github'
    template_dir.mkdir()
    template_file = template_dir / 'PULL_REQUEST_TEMPLATE.md'
    template_file.write_text('### What does this PR do?\n\n<!-- describe -->\n\n### Motivation\n')
    app_mock.repo.path = tmp_path

    body = build_pr_body(app_mock, sha='abcdef1234567890', subject='Fix bug', target='7.62.x', original_pr='12345')

    assert '**Backported commit**: `abcdef1234`' in body
    assert '**Original PR**: #12345' in body
    assert '**Target branch**: `7.62.x`' in body
    assert '### Motivation' in body


def test_build_pr_body_without_template(app_mock, tmp_path):
    app_mock.repo.path = tmp_path

    body = build_pr_body(app_mock, sha='abcdef1234567890', subject='Fix bug', target='master', original_pr=None)

    assert '### What does this PR do?' in body
    assert '**Backported commit**: `abcdef1234`' in body
    assert 'Original PR' not in body


class _RunnableStep(PortStep):
    def __init__(self, app, *, fail=False, dry_run=False):
        super().__init__(app, dry_run=dry_run)
        self.fail = fail
        self.executed = False

    def describe(self):
        return 'Doing the thing'

    def planned_commands(self):
        return ['echo hi']

    def execute(self):
        self.executed = True
        if self.fail:
            raise OSError('boom')


def test_port_step_dry_run_skips_execute(app_mock):
    step = _RunnableStep(app_mock, dry_run=True)
    step.run()
    assert step.executed is False
    app_mock.status.assert_not_called()
    info_calls = [c.args[0] for c in app_mock.display_info.call_args_list]
    assert 'Doing the thing' in info_calls
    assert any('echo hi' in line for line in info_calls)


def test_port_step_executes_and_emits_success(app_mock):
    step = _RunnableStep(app_mock)
    step.run()
    assert step.executed is True
    app_mock.status.assert_called_once_with('Doing the thing')
    app_mock.display_success.assert_called_once()


def test_port_step_wraps_oserror_as_port_step_error(app_mock):
    step = _RunnableStep(app_mock, fail=True)
    with pytest.raises(PortStepError, match='boom'):
        step.run()


def test_cherry_pick_clean(app_mock):
    step = CherryPickStep(app_mock, sha='deadbeef00')
    step.execute()
    app_mock.repo.git.run.assert_called_once_with('cherry-pick', '--no-commit', 'deadbeef00')
    app_mock.repo.git.capture.assert_not_called()


def test_cherry_pick_only_in_toto_conflict_is_resolved(app_mock):
    app_mock.repo.git.run.side_effect = [OSError('conflict'), None, None]
    app_mock.repo.git.capture.side_effect = [
        'path/file.in-toto.link\n',
        '',
    ]

    step = CherryPickStep(app_mock, sha='deadbeef00')
    step.execute()

    assert app_mock.repo.git.run.call_args_list == [
        call('cherry-pick', '--no-commit', 'deadbeef00'),
        call('checkout', '--ours', 'path/file.in-toto.link'),
        call('add', 'path/file.in-toto.link'),
    ]


def test_cherry_pick_mixed_conflict_aborts(app_mock):
    app_mock.repo.git.run.side_effect = [OSError('conflict'), None]
    app_mock.repo.git.capture.return_value = 'src/foo.py\npath/file.in-toto.link\n'

    step = CherryPickStep(app_mock, sha='deadbeef00')
    with pytest.raises(PortStepError, match='non-`.in-toto`'):
        step.execute()

    app_mock.repo.git.run.assert_any_call('cherry-pick', '--abort')


def test_cherry_pick_failure_without_conflicts_aborts(app_mock):
    app_mock.repo.git.run.side_effect = OSError('conflict')
    app_mock.repo.git.capture.return_value = ''

    step = CherryPickStep(app_mock, sha='deadbeef00')
    with pytest.raises(PortStepError, match='without conflicts'):
        step.execute()


def test_preserve_in_toto_resets_staged_modifications(app_mock):
    app_mock.repo.git.capture.side_effect = [
        'src/foo.py\npath/file.in-toto.link\n',
        '',
    ]

    step = PreserveInTotoStep(app_mock)
    step.execute()

    app_mock.repo.git.run.assert_called_once_with('checkout', 'HEAD', '--', 'path/file.in-toto.link')


def test_preserve_in_toto_removes_files_not_in_head(app_mock):
    app_mock.repo.git.capture.side_effect = [
        'path/new.in-toto.link\n',
        OSError('not in head'),
    ]

    step = PreserveInTotoStep(app_mock)
    step.execute()

    app_mock.repo.git.run.assert_called_once_with('rm', '--force', 'path/new.in-toto.link')


def test_preserve_in_toto_noop_when_clean(app_mock):
    app_mock.repo.git.capture.return_value = 'src/foo.py\n'

    step = PreserveInTotoStep(app_mock)
    step.execute()

    app_mock.repo.git.run.assert_not_called()


@pytest.mark.parametrize(
    'verify,expected_args',
    [
        (False, ('commit', '--no-verify', '-m', '[Backport] Fix bug')),
        (True, ('commit', '-m', '[Backport] Fix bug')),
    ],
)
def test_commit_step(app_mock, verify, expected_args):
    step = CommitStep(app_mock, subject='Fix bug', verify=verify)
    step.execute()
    app_mock.repo.git.run.assert_called_once_with(*expected_args)


def test_create_pull_request_step(app_mock: MagicMock, fake_async_github: FakeAsyncGitHubClient) -> None:
    app_mock.config.github.token = 'ghp_test'
    fake_async_github.mock_response(
        'create_pull_request',
        PullRequest(number=7, html_url='https://github.com/x/pr/1'),
    )

    step = CreatePullRequestStep(
        app_mock,
        owner='DataDog',
        repo='integrations-core',
        title='[Backport] Fix bug',
        head='alice/port-deadbeef00-to-7.62.x',
        base='7.62.x',
        body='body',
        labels=['qa/skip-qa'],
        draft=False,
    )
    step.execute()

    fake_async_github.assert_called_once_with(
        'create_pull_request',
        owner='DataDog',
        repo='integrations-core',
        title='[Backport] Fix bug',
        head='alice/port-deadbeef00-to-7.62.x',
        base='7.62.x',
        body='body',
        draft=False,
    )
    fake_async_github.assert_called_once_with(
        'add_labels_to_issue',
        owner='DataDog',
        repo='integrations-core',
        issue_number=7,
        labels=['qa/skip-qa'],
    )
    assert step.pr_url == 'https://github.com/x/pr/1'


def test_create_pull_request_step_skips_label_call_when_no_labels(
    app_mock: MagicMock, fake_async_github: FakeAsyncGitHubClient
) -> None:
    app_mock.config.github.token = 'ghp_test'

    step = CreatePullRequestStep(
        app_mock,
        owner='DataDog',
        repo='integrations-core',
        title='[Backport] Fix',
        head='alice/x',
        base='master',
        body='body',
        labels=[],
        draft=True,
    )
    step.execute()

    fake_async_github.assert_called_once_with(
        'create_pull_request',
        owner='DataDog',
        repo='integrations-core',
        title='[Backport] Fix',
        head='alice/x',
        base='master',
        body='body',
        draft=True,
    )
    fake_async_github.assert_not_called('add_labels_to_issue')


def _setup_command_mocks(mocker, *, commit_sha='deadbeef0011223344', subject='Fix bug (#100)', in_toto=''):
    mocker.patch('ddev.utils.git.GitRepository.run')
    capture_mock = mocker.patch('ddev.utils.git.GitRepository.capture')
    capture_mock.side_effect = lambda *args: {
        ('rev-parse', '--verify', f'{commit_sha}^{{commit}}'): commit_sha + '\n',
        ('diff-tree', '--no-commit-id', '--name-only', '-r', commit_sha): in_toto,
    }.get(args, '')
    mocker.patch(
        'ddev.utils.git.GitRepository.log',
        return_value=[{'hash': commit_sha, 'subject': subject}],
    )
    mocker.patch(
        'ddev.utils.git.GitRepository.latest_commit',
        return_value=GitCommit(commit_sha, subject=subject),
    )


def test_command_happy_path(ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient) -> None:
    _setup_command_mocks(mocker)
    fake_async_github.mock_response(
        'create_pull_request',
        PullRequest(number=1, html_url='https://github.com/x/pr/1'),
    )
    mocker.patch('click.confirm', return_value=True)
    mocker.patch.dict('os.environ', {'DD_GITHUB_USER': 'alice'})

    result = ddev('release', 'port-commit', 'deadbeef0011223344')

    assert result.exit_code == 0, result.output
    assert 'Pull request created: https://github.com/x/pr/1' in result.output

    pr_call = fake_async_github.last_call('create_pull_request')
    assert pr_call.kwargs['owner'] == 'DataDog'
    assert pr_call.kwargs['repo'] == 'integrations-core'
    assert pr_call.kwargs['title'] == '[Backport] Fix bug'
    assert pr_call.kwargs['head'] == 'alice/port-deadbeef00-to-master'
    assert pr_call.kwargs['base'] == 'master'
    assert pr_call.kwargs['draft'] is False
    assert '**Backported commit**: `deadbeef00`' in pr_call.kwargs['body']
    assert '**Original PR**: #100' in pr_call.kwargs['body']

    fake_async_github.assert_called_once_with(
        'add_labels_to_issue',
        owner='DataDog',
        repo='integrations-core',
        issue_number=1,
        labels=['qa/skip-qa'],
    )


def test_command_draft_flag(ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient) -> None:
    _setup_command_mocks(mocker)
    mocker.patch('click.confirm', return_value=True)
    mocker.patch.dict('os.environ', {'DD_GITHUB_USER': 'alice'})

    result = ddev('release', 'port-commit', '--draft', 'deadbeef0011223344')

    assert result.exit_code == 0, result.output
    assert fake_async_github.last_call('create_pull_request').kwargs['draft'] is True


def test_command_no_pr(ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient) -> None:
    _setup_command_mocks(mocker)
    mocker.patch('click.confirm', return_value=True)
    mocker.patch.dict('os.environ', {'DD_GITHUB_USER': 'alice'})

    result = ddev('release', 'port-commit', '--no-pr', 'deadbeef0011223344')

    assert result.exit_code == 0, result.output
    fake_async_github.assert_not_called('create_pull_request')
    fake_async_github.assert_not_called('add_labels_to_issue')


def test_command_dry_run_makes_no_mutating_calls(
    ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient
) -> None:
    _setup_command_mocks(mocker)
    run_mock = mocker.patch('ddev.utils.git.GitRepository.run')
    mocker.patch.dict('os.environ', {'DD_GITHUB_USER': 'alice'})

    result = ddev('release', 'port-commit', '--dry-run', 'deadbeef0011223344')

    assert result.exit_code == 0, result.output
    assert '(dry-run)' in result.output
    run_mock.assert_not_called()
    fake_async_github.assert_not_called('create_pull_request')


def test_command_aborts_when_no_github_user(ddev: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch.dict('os.environ', {'DD_GITHUB_USER': '', 'GITHUB_USER': '', 'GITHUB_ACTOR': ''})

    result = ddev('release', 'port-commit', 'deadbeef0011223344')

    assert result.exit_code == 1, result.output
    assert 'No GitHub user configured' in result.output


def test_command_aborts_on_unconfirmed(
    ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient
) -> None:
    _setup_command_mocks(mocker)
    mocker.patch('click.confirm', return_value=False)
    mocker.patch.dict('os.environ', {'DD_GITHUB_USER': 'alice'})

    result = ddev('release', 'port-commit', 'deadbeef0011223344')

    assert result.exit_code == 1, result.output
    assert 'Did not get confirmation' in result.output
    fake_async_github.assert_not_called('create_pull_request')


def test_command_uses_head_when_no_commit_given(
    ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient
) -> None:
    _setup_command_mocks(mocker)
    mocker.patch('click.confirm', return_value=True)
    mocker.patch.dict('os.environ', {'DD_GITHUB_USER': 'alice'})

    result = ddev('release', 'port-commit')

    assert result.exit_code == 0, result.output
    assert 'No commit specified' in result.output
    assert len(fake_async_github.calls_to('create_pull_request')) == 1
