# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from pathlib import Path as StdPath
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
    SetupWorktreeStep,
    TeardownWorktreeStep,
    build_pr_body,
    parse_labels,
    split_commit_subject,
)
from ddev.utils.git import GitCommit
from ddev.utils.github_async.models import PullRequest
from tests.helpers.github_async import FakeAsyncGitHubClient
from tests.helpers.runner import CliRunner

FULL_SHA_FOR_TESTS = '1234567890abcdef001234567890abcdef00abcd'


@pytest.fixture
def app_mock(mocker: MockerFixture) -> MagicMock:
    app = mocker.MagicMock()
    app.status.return_value.__enter__ = MagicMock(return_value=None)
    app.status.return_value.__exit__ = MagicMock(return_value=None)
    return app


@pytest.fixture
def git_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.MagicMock()


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

    body = build_pr_body(
        app_mock,
        sha='abcdef1234567890',
        subject='Fix bug',
        target='7.62.x',
        original_pr='12345',
        owner='DataDog',
        repo='integrations-core',
    )

    assert (
        '**Backported commit**: [`abcdef1234`](https://github.com/DataDog/integrations-core/commit/abcdef1234567890)'
        in body
    )
    assert '**Original PR**: #12345' in body
    assert '**Target branch**: `7.62.x`' in body
    assert '### Motivation' in body


def test_build_pr_body_without_template(app_mock, tmp_path):
    app_mock.repo.path = tmp_path

    body = build_pr_body(
        app_mock,
        sha='abcdef1234567890',
        subject='Fix bug',
        target='master',
        original_pr=None,
        owner='DataDog',
        repo='integrations-core',
    )

    assert '### What does this PR do?' in body
    assert (
        '**Backported commit**: [`abcdef1234`](https://github.com/DataDog/integrations-core/commit/abcdef1234567890)'
        in body
    )
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
    app_mock.status.assert_not_called()
    output_text = ' '.join(str(c.args[0]) for c in app_mock.output.call_args_list)
    assert 'Doing the thing...' in output_text
    assert 'Doing the thing: done.' in output_text


def test_port_step_wraps_oserror_as_port_step_error(app_mock):
    step = _RunnableStep(app_mock, fail=True)
    with pytest.raises(PortStepError, match='boom'):
        step.run()


def test_setup_worktree_step_creates_branch_in_worktree(app_mock, git_mock, tmp_path):
    worktree_path = tmp_path / '.worktrees' / 'port-commit' / 'alice-port-1234567890-to-master'

    step = SetupWorktreeStep(
        app_mock,
        main_git=git_mock,
        worktree_path=worktree_path,
        branch='alice/port-1234567890-to-master',
        target='master',
    )
    step.execute()

    git_mock.run.assert_called_once_with(
        'worktree', 'add', '-B', 'alice/port-1234567890-to-master', str(worktree_path), 'origin/master'
    )
    assert worktree_path.parent.is_dir()


def test_setup_worktree_step_wraps_oserror_as_port_step_error(app_mock, git_mock, tmp_path):
    git_mock.run.side_effect = OSError('already exists')

    step = SetupWorktreeStep(
        app_mock,
        main_git=git_mock,
        worktree_path=tmp_path / '.worktrees' / 'port-commit' / 'alice-x',
        branch='alice/x',
        target='master',
    )
    with pytest.raises(PortStepError, match='Failed to create worktree'):
        step.execute()


def test_teardown_worktree_step_removes_worktree(app_mock, git_mock, tmp_path):
    worktree_path = tmp_path / '.worktrees' / 'port-commit' / 'alice-x'

    step = TeardownWorktreeStep(app_mock, main_git=git_mock, worktree_path=worktree_path)
    step.execute()

    git_mock.run.assert_called_once_with('worktree', 'remove', '--force', str(worktree_path))


def test_cherry_pick_clean(app_mock, git_mock):
    step = CherryPickStep(app_mock, git=git_mock, sha='1234567890')
    step.execute()
    git_mock.run.assert_called_once_with('cherry-pick', '--no-commit', '1234567890')
    git_mock.capture.assert_not_called()


def test_cherry_pick_only_in_toto_conflict_is_resolved(app_mock, git_mock):
    git_mock.run.side_effect = [OSError('conflict'), None, None]
    git_mock.capture.side_effect = [
        'path/file.in-toto.link\n',
        '',
    ]

    step = CherryPickStep(app_mock, git=git_mock, sha='1234567890')
    step.execute()

    assert git_mock.run.call_args_list == [
        call('cherry-pick', '--no-commit', '1234567890'),
        call('checkout', '--ours', 'path/file.in-toto.link'),
        call('add', 'path/file.in-toto.link'),
    ]


def test_cherry_pick_mixed_conflict_aborts(app_mock, git_mock):
    git_mock.run.side_effect = [OSError('conflict'), None]
    git_mock.capture.return_value = 'src/foo.py\npath/file.in-toto.link\n'

    step = CherryPickStep(app_mock, git=git_mock, sha='1234567890')
    with pytest.raises(PortStepError, match='non-`.in-toto`'):
        step.execute()

    git_mock.run.assert_any_call('cherry-pick', '--abort')


def test_cherry_pick_failure_without_conflicts_aborts(app_mock, git_mock):
    git_mock.run.side_effect = OSError('conflict')
    git_mock.capture.return_value = ''

    step = CherryPickStep(app_mock, git=git_mock, sha='1234567890')
    with pytest.raises(PortStepError, match='without conflicts'):
        step.execute()


def test_preserve_in_toto_resets_staged_modifications(app_mock, git_mock):
    git_mock.capture.side_effect = [
        'src/foo.py\npath/file.in-toto.link\n',
        '',
    ]

    step = PreserveInTotoStep(app_mock, git=git_mock)
    step.execute()

    git_mock.run.assert_called_once_with('checkout', 'HEAD', '--', 'path/file.in-toto.link')


def test_preserve_in_toto_removes_files_not_in_head(app_mock, git_mock):
    git_mock.capture.side_effect = [
        'path/new.in-toto.link\n',
        OSError('not in head'),
    ]

    step = PreserveInTotoStep(app_mock, git=git_mock)
    step.execute()

    git_mock.run.assert_called_once_with('rm', '--force', 'path/new.in-toto.link')


def test_preserve_in_toto_noop_when_clean(app_mock, git_mock):
    git_mock.capture.return_value = 'src/foo.py\n'

    step = PreserveInTotoStep(app_mock, git=git_mock)
    step.execute()

    git_mock.run.assert_not_called()


@pytest.mark.parametrize(
    'verify,expected_args',
    [
        (False, ('commit', '--no-verify', '-m', '[Backport] Fix bug')),
        (True, ('commit', '-m', '[Backport] Fix bug')),
    ],
)
def test_commit_step(app_mock, git_mock, verify, expected_args):
    step = CommitStep(app_mock, git=git_mock, subject='Fix bug', verify=verify)
    step.execute()
    git_mock.run.assert_called_once_with(*expected_args)


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
        head='alice/port-1234567890-to-7.62.x',
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
        head='alice/port-1234567890-to-7.62.x',
        base='7.62.x',
        body='body',
        draft=False,
        timeout=None,
    )
    fake_async_github.assert_called_once_with(
        'add_labels_to_issue',
        owner='DataDog',
        repo='integrations-core',
        issue_number=7,
        labels=['qa/skip-qa'],
        timeout=None,
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
        timeout=None,
    )
    fake_async_github.assert_not_called('add_labels_to_issue')


def _setup_command_mocks(
    mocker,
    *,
    commit_sha='1234567890abcdef00',
    subject='Fix bug (#100)',
    in_toto='',
    parents=('parent_sha',),
):
    """Patch git so the workflow sees a resolvable commit. `parents` controls the merge-parent check."""
    run_mock = mocker.patch('ddev.utils.git.GitRepository.run')
    capture_mock = mocker.patch('ddev.utils.git.GitRepository.capture')
    rev_list_output = ' '.join([commit_sha, *parents]) + '\n'
    capture_mock.side_effect = lambda *args: {
        ('rev-parse', '--verify', f'{commit_sha}^{{commit}}'): commit_sha + '\n',
        ('diff-tree', '--no-commit-id', '--name-only', '-r', commit_sha): in_toto,
        ('rev-list', '--parents', '-n1', commit_sha): rev_list_output,
    }.get(args, '')
    mocker.patch(
        'ddev.utils.git.GitRepository.log',
        return_value=[{'hash': commit_sha, 'subject': subject}],
    )
    mocker.patch(
        'ddev.utils.git.GitRepository.latest_commit',
        return_value=GitCommit(commit_sha, subject=subject),
    )
    return run_mock


def _merged_pr(number=23703, merge_commit_sha=None):
    """Build a PullRequest model for a squash-merged PR."""
    return PullRequest(
        number=number,
        html_url=f'https://github.com/DataDog/integrations-core/pull/{number}',
        merged=True,
        merge_commit_sha=merge_commit_sha or FULL_SHA_FOR_TESTS,
    )


def test_command_happy_path(ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient) -> None:
    run_mock = _setup_command_mocks(mocker)
    fake_async_github.mock_response(
        'create_pull_request',
        PullRequest(number=1, html_url='https://github.com/x/pr/1'),
    )
    mocker.patch('click.confirm', return_value=True)
    mocker.patch.dict('os.environ', {'DD_GITHUB_USER': 'alice'})

    result = ddev('release', 'port-commit', '1234567890abcdef00')

    assert result.exit_code == 0, result.output
    assert 'Backport completed' in result.output
    assert 'https://github.com/x/pr/1' in result.output

    pr_call = fake_async_github.last_call('create_pull_request')
    assert pr_call.kwargs['owner'] == 'DataDog'
    assert pr_call.kwargs['repo'] == 'integrations-core'
    assert pr_call.kwargs['title'] == '[Backport] Fix bug'
    assert pr_call.kwargs['head'] == 'alice/port-1234567890-to-master'
    assert pr_call.kwargs['base'] == 'master'
    assert pr_call.kwargs['draft'] is False
    assert (
        '**Backported commit**: [`1234567890`](https://github.com/DataDog/integrations-core/commit/1234567890abcdef00)'
        in pr_call.kwargs['body']
    )
    assert '**Original PR**: #100' in pr_call.kwargs['body']

    fake_async_github.assert_called_once_with(
        'add_labels_to_issue',
        owner='DataDog',
        repo='integrations-core',
        issue_number=1,
        labels=['qa/skip-qa'],
        timeout=None,
    )

    git_calls = [c.args for c in run_mock.call_args_list]
    assert ('fetch', 'origin') in git_calls
    assert any(args[:2] == ('worktree', 'add') for args in git_calls)
    assert any(args[:3] == ('worktree', 'remove', '--force') for args in git_calls)


def test_command_lowercases_branch_name(
    ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient
) -> None:
    run_mock = _setup_command_mocks(mocker)
    fake_async_github.mock_response(
        'create_pull_request',
        PullRequest(number=1, html_url='https://github.com/x/pr/1'),
    )
    mocker.patch('click.confirm', return_value=True)
    mocker.patch.dict('os.environ', {'DD_GITHUB_USER': 'AAraKKe'})

    result = ddev('release', 'port-commit', '1234567890abcdef00')

    assert result.exit_code == 0, result.output
    assert fake_async_github.last_call('create_pull_request').kwargs['head'] == 'aarakke/port-1234567890-to-master'

    worktree_add = next(args for args in (c.args for c in run_mock.call_args_list) if args[:2] == ('worktree', 'add'))
    assert 'aarakke/port-1234567890-to-master' in worktree_add
    assert all('AAraKKe' not in str(part) for part in worktree_add)


def test_command_draft_flag(ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient) -> None:
    _setup_command_mocks(mocker)
    mocker.patch('click.confirm', return_value=True)
    mocker.patch.dict('os.environ', {'DD_GITHUB_USER': 'alice'})

    result = ddev('release', 'port-commit', '--draft', '1234567890abcdef00')

    assert result.exit_code == 0, result.output
    assert fake_async_github.last_call('create_pull_request').kwargs['draft'] is True


def test_command_no_pr(ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient) -> None:
    _setup_command_mocks(mocker)
    mocker.patch('click.confirm', return_value=True)
    mocker.patch.dict('os.environ', {'DD_GITHUB_USER': 'alice'})

    result = ddev('release', 'port-commit', '--no-pr', '1234567890abcdef00')

    assert result.exit_code == 0, result.output
    fake_async_github.assert_not_called('create_pull_request')
    fake_async_github.assert_not_called('add_labels_to_issue')


def test_command_dry_run_makes_no_mutating_calls(
    ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient
) -> None:
    run_mock = _setup_command_mocks(mocker)
    mocker.patch.dict('os.environ', {'DD_GITHUB_USER': 'alice'})

    result = ddev('release', 'port-commit', '--dry-run', '1234567890abcdef00')

    assert result.exit_code == 0, result.output
    assert '(dry-run)' in result.output
    run_mock.assert_not_called()
    fake_async_github.assert_not_called('create_pull_request')


def test_create_pull_request_step_reports_partial_failure_when_labeling_fails(
    app_mock: MagicMock, fake_async_github: FakeAsyncGitHubClient
) -> None:
    import httpx

    app_mock.config.github.token = 'ghp_test'
    fake_async_github.mock_response(
        'create_pull_request',
        PullRequest(number=7, html_url='https://github.com/x/pr/7'),
    )
    fake_async_github.mock_response(
        'add_labels_to_issue',
        httpx.HTTPStatusError('forbidden', request=httpx.Request('POST', 'https://x'), response=httpx.Response(403)),
    )

    step = CreatePullRequestStep(
        app_mock,
        owner='DataDog',
        repo='integrations-core',
        title='[Backport] Fix bug',
        head='alice/x',
        base='master',
        body='body',
        labels=['qa/skip-qa'],
        draft=False,
    )

    with pytest.raises(PortStepError, match=r'created at https://github.com/x/pr/7 but labeling failed'):
        step.execute()

    assert step.pr_url == 'https://github.com/x/pr/7'


def test_command_suppresses_worktree_warning_on_partial_pr_failure(
    ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient
) -> None:
    import httpx

    _setup_command_mocks(mocker)
    fake_async_github.mock_response(
        'create_pull_request',
        PullRequest(number=1, html_url='https://github.com/x/pr/1'),
    )
    fake_async_github.mock_response(
        'add_labels_to_issue',
        httpx.HTTPStatusError('forbidden', request=httpx.Request('POST', 'https://x'), response=httpx.Response(403)),
    )
    mocker.patch('click.confirm', return_value=True)
    mocker.patch.dict('os.environ', {'DD_GITHUB_USER': 'alice'})

    result = ddev('release', 'port-commit', '1234567890abcdef00')

    assert result.exit_code == 1, result.output
    assert 'Pull request created at https://github.com/x/pr/1 but labeling failed' in result.output
    assert 'Worktree left at' not in result.output


def test_command_leaves_worktree_on_failure(
    ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient
) -> None:
    run_mock = _setup_command_mocks(mocker)

    def run_side_effect(*args):
        if args[:2] == ('worktree', 'add'):
            raise OSError('refusing to overwrite existing worktree')
        return None

    run_mock.side_effect = run_side_effect
    mocker.patch('click.confirm', return_value=True)
    mocker.patch.dict('os.environ', {'DD_GITHUB_USER': 'alice'})

    result = ddev('release', 'port-commit', '1234567890abcdef00')

    assert result.exit_code == 1, result.output
    assert 'Worktree left at' in result.output
    assert 'Failed to create worktree' in result.output
    git_calls = [c.args for c in run_mock.call_args_list]
    assert not any(args[:3] == ('worktree', 'remove', '--force') for args in git_calls)


def test_command_aborts_when_no_github_user(ddev: CliRunner, mocker: MockerFixture) -> None:
    mocker.patch.dict('os.environ', {'DD_GITHUB_USER': '', 'GITHUB_USER': '', 'GITHUB_ACTOR': ''})

    result = ddev('release', 'port-commit', '1234567890abcdef00')

    assert result.exit_code == 1, result.output
    assert 'No GitHub user configured' in result.output


@pytest.mark.parametrize(
    'extra_args,expected_exit,expected_output',
    [
        pytest.param([], 1, 'No GitHub token configured', id='pr-requested-aborts'),
        pytest.param(['--no-pr'], 0, '', id='no-pr-allows-missing-token'),
    ],
)
def test_command_token_guard(
    ddev: CliRunner,
    mocker: MockerFixture,
    fake_async_github: FakeAsyncGitHubClient,
    extra_args: list[str],
    expected_exit: int,
    expected_output: str,
) -> None:
    _setup_command_mocks(mocker)
    mocker.patch('click.confirm', return_value=True)
    mocker.patch.dict(
        'os.environ',
        {'DD_GITHUB_USER': 'alice', 'DD_GITHUB_TOKEN': '', 'GH_TOKEN': '', 'GITHUB_TOKEN': ''},
    )

    result = ddev('release', 'port-commit', *extra_args, '1234567890abcdef00')

    assert result.exit_code == expected_exit, result.output
    if expected_output:
        assert expected_output in result.output
    fake_async_github.assert_not_called('create_pull_request')


def test_command_aborts_when_commit_missing_after_fetch(
    ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient
) -> None:
    """Fetch succeeds but rev-parse still cannot resolve the commit (edge case)."""
    run_mock = mocker.patch('ddev.utils.git.GitRepository.run')
    mocker.patch('ddev.utils.git.GitRepository.capture', side_effect=OSError('bad object'))
    mocker.patch.dict('os.environ', {'DD_GITHUB_USER': 'alice'})

    result = ddev('release', 'port-commit', FULL_SHA_FOR_TESTS)

    assert result.exit_code == 1, result.output
    assert 'does not exist locally or on origin' in result.output
    assert ('fetch', 'origin', FULL_SHA_FOR_TESTS) in [c.args for c in run_mock.call_args_list]
    fake_async_github.assert_not_called('create_pull_request')


def test_command_aborts_when_fetch_fails(
    ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient
) -> None:
    def run_side_effect(*args):
        if args[:2] == ('fetch', 'origin'):
            raise OSError("couldn't find remote ref")
        return None

    mocker.patch('ddev.utils.git.GitRepository.run', side_effect=run_side_effect)
    mocker.patch('ddev.utils.git.GitRepository.capture', side_effect=OSError('bad object'))
    mocker.patch.dict('os.environ', {'DD_GITHUB_USER': 'alice'})

    result = ddev('release', 'port-commit', FULL_SHA_FOR_TESTS)

    assert result.exit_code == 1, result.output
    assert 'does not exist locally or on origin' in result.output
    fake_async_github.assert_not_called('create_pull_request')


def test_command_aborts_in_dry_run_when_commit_not_local(
    ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient
) -> None:
    """Dry-run must not mutate local state, so don't fetch when the commit is missing."""
    run_mock = mocker.patch('ddev.utils.git.GitRepository.run')
    mocker.patch('ddev.utils.git.GitRepository.capture', side_effect=OSError('bad object'))
    mocker.patch.dict('os.environ', {'DD_GITHUB_USER': 'alice'})

    result = ddev('release', 'port-commit', '--dry-run', FULL_SHA_FOR_TESTS)

    assert result.exit_code == 1, result.output
    assert 'is not in the local repository' in result.output
    assert 'Re-run without `--dry-run`' in result.output
    assert not any(c.args[:2] == ('fetch', 'origin') for c in run_mock.call_args_list)
    fake_async_github.assert_not_called('create_pull_request')


def test_command_aborts_on_abbreviated_sha_not_local(
    ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient
) -> None:
    """Abbreviated SHAs cannot be fetched from origin, so abort early with a clear hint."""
    run_mock = mocker.patch('ddev.utils.git.GitRepository.run')
    mocker.patch('ddev.utils.git.GitRepository.capture', side_effect=OSError('bad object'))
    mocker.patch.dict('os.environ', {'DD_GITHUB_USER': 'alice'})

    result = ddev('release', 'port-commit', '1234567890')

    assert result.exit_code == 1, result.output
    assert 'full 40-character SHA' in result.output
    assert not any(c.args[:2] == ('fetch', 'origin') for c in run_mock.call_args_list)
    fake_async_github.assert_not_called('create_pull_request')


def test_command_fetches_commit_when_not_local(
    ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient
) -> None:
    commit_sha = FULL_SHA_FOR_TESTS
    subject = 'Fix bug (#100)'
    rev_parse_calls = {'count': 0}

    def capture_side_effect(*args):
        if args == ('rev-parse', '--verify', f'{commit_sha}^{{commit}}'):
            rev_parse_calls['count'] += 1
            if rev_parse_calls['count'] == 1:
                raise OSError('bad object')
            return commit_sha + '\n'
        if args == ('diff-tree', '--no-commit-id', '--name-only', '-r', commit_sha):
            return ''
        return ''

    run_mock = mocker.patch('ddev.utils.git.GitRepository.run')
    mocker.patch('ddev.utils.git.GitRepository.capture', side_effect=capture_side_effect)
    mocker.patch(
        'ddev.utils.git.GitRepository.log',
        return_value=[{'hash': commit_sha, 'subject': subject}],
    )
    fake_async_github.mock_response(
        'create_pull_request',
        PullRequest(number=1, html_url='https://github.com/x/pr/1'),
    )
    mocker.patch('click.confirm', return_value=True)
    mocker.patch.dict('os.environ', {'DD_GITHUB_USER': 'alice'})

    result = ddev('release', 'port-commit', commit_sha)

    assert result.exit_code == 0, result.output
    assert 'not found locally; fetching from origin' in result.output
    assert rev_parse_calls['count'] == 2
    git_calls = [c.args for c in run_mock.call_args_list]
    assert ('fetch', 'origin', commit_sha) in git_calls
    fake_async_github.assert_called_once_with(
        'create_pull_request',
        owner='DataDog',
        repo='integrations-core',
        title='[Backport] Fix bug',
        head=f'alice/port-{commit_sha[:10]}-to-master',
        base='master',
        body=mocker.ANY,
        draft=False,
        timeout=None,
    )


@pytest.mark.parametrize(
    'input_arg',
    [
        pytest.param('PR-23703', id='PR-prefix'),
        pytest.param('pr-23703', id='PR-prefix-lowercase'),
        pytest.param('PR-23703 ', id='PR-prefix-trailing-whitespace'),
        pytest.param('https://github.com/DataDog/integrations-core/pull/23703', id='URL-https'),
        pytest.param('http://github.com/DataDog/integrations-core/pull/23703', id='URL-http'),
        pytest.param('https://github.com/DataDog/integrations-core/pull/23703#discussion_r1', id='URL-with-fragment'),
        pytest.param('23703', id='pure-digit-auto-detect'),
        pytest.param(' 23703 ', id='pure-digit-with-whitespace'),
    ],
)
def test_command_resolves_pr_input(
    input_arg: str,
    ddev: CliRunner,
    mocker: MockerFixture,
    fake_async_github: FakeAsyncGitHubClient,
) -> None:
    _setup_command_mocks(mocker, commit_sha=FULL_SHA_FOR_TESTS)
    fake_async_github.mock_response('get_pull_request', _merged_pr(number=23703))
    fake_async_github.mock_response(
        'create_pull_request',
        PullRequest(number=1, html_url='https://github.com/x/pr/1'),
    )
    mocker.patch('click.confirm', return_value=True)
    mocker.patch.dict('os.environ', {'DD_GITHUB_USER': 'alice'})

    result = ddev('release', 'port-commit', input_arg)

    assert result.exit_code == 0, result.output
    pr_call = fake_async_github.last_call('get_pull_request')
    assert pr_call.kwargs['owner'] == 'DataDog'
    assert pr_call.kwargs['repo'] == 'integrations-core'
    assert pr_call.kwargs['pull_number'] == 23703


def test_command_aborts_when_pr_not_merged(
    ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient
) -> None:
    _setup_command_mocks(mocker, commit_sha=FULL_SHA_FOR_TESTS)
    fake_async_github.mock_response(
        'get_pull_request',
        PullRequest(
            number=23703,
            html_url='https://github.com/DataDog/integrations-core/pull/23703',
            merged=False,
            merge_commit_sha=None,
        ),
    )
    mocker.patch.dict('os.environ', {'DD_GITHUB_USER': 'alice'})

    result = ddev('release', 'port-commit', 'PR-23703')

    assert result.exit_code == 1, result.output
    assert 'PR #23703 is not merged' in result.output


def test_command_aborts_when_pr_is_merge_commit(
    ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient
) -> None:
    _setup_command_mocks(mocker, commit_sha=FULL_SHA_FOR_TESTS, parents=('parent1', 'parent2'))
    fake_async_github.mock_response('get_pull_request', _merged_pr(number=23703))
    mocker.patch.dict('os.environ', {'DD_GITHUB_USER': 'alice'})

    result = ddev('release', 'port-commit', 'PR-23703')

    assert result.exit_code == 1, result.output
    assert 'not squash-merged' in result.output
    assert 'specific commit' in result.output.lower()


def test_command_emits_pr_context_when_pure_digit_pr_merge_commit_missing(
    ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient
) -> None:
    """Pure-digit PR input + PR found + non-resolvable merge commit -> abort names the PR, not the SHA."""
    fake_async_github.mock_response('get_pull_request', _merged_pr(number=23703))
    mocker.patch('ddev.utils.git.GitRepository.run')
    mocker.patch('ddev.utils.git.GitRepository.capture', side_effect=OSError('bad object'))
    mocker.patch.dict('os.environ', {'DD_GITHUB_USER': 'alice'})

    result = ddev('release', 'port-commit', '--dry-run', '23703')

    assert result.exit_code == 1, result.output
    assert 'PR #23703 was found but its merge commit' in result.output
    assert FULL_SHA_FOR_TESTS in result.output


def test_command_aborts_when_pr_input_has_no_token(
    ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient
) -> None:
    """Explicit PR form requires a GitHub token even with --no-pr."""
    mocker.patch.dict(
        'os.environ',
        {'DD_GITHUB_USER': 'alice', 'DD_GITHUB_TOKEN': '', 'GH_TOKEN': '', 'GITHUB_TOKEN': ''},
    )

    result = ddev('release', 'port-commit', '--no-pr', 'PR-23703')

    assert result.exit_code == 1, result.output
    assert 'GitHub token required to resolve a PR reference' in result.output
    assert '--no-pr does not skip this lookup' in result.output
    fake_async_github.assert_not_called('get_pull_request')


def test_command_falls_back_to_commit_on_pr_not_found(
    ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient
) -> None:
    """Pure-digit input that isn't a PR resolves as a commit when it's local (PR 404 from default mock)."""
    short_input = '1234'
    full_sha = FULL_SHA_FOR_TESTS
    run_mock = mocker.patch('ddev.utils.git.GitRepository.run')
    capture_mock = mocker.patch('ddev.utils.git.GitRepository.capture')
    capture_mock.side_effect = lambda *args: {
        ('rev-parse', '--verify', f'{short_input}^{{commit}}'): full_sha + '\n',
        ('diff-tree', '--no-commit-id', '--name-only', '-r', full_sha): '',
    }.get(args, '')
    mocker.patch('ddev.utils.git.GitRepository.log', return_value=[{'hash': full_sha, 'subject': 'Fix bug'}])
    fake_async_github.mock_response(
        'create_pull_request',
        PullRequest(number=1, html_url='https://github.com/x/pr/1'),
    )
    mocker.patch('click.confirm', return_value=True)
    mocker.patch.dict('os.environ', {'DD_GITHUB_USER': 'alice'})

    result = ddev('release', 'port-commit', short_input)

    assert result.exit_code == 0, result.output
    assert fake_async_github.last_call('get_pull_request').kwargs['pull_number'] == int(short_input)
    git_calls = [c.args for c in run_mock.call_args_list]
    # No SHA-targeted fetch (3 args): commit was resolvable locally.
    assert not any(len(args) == 3 and args[:2] == ('fetch', 'origin') for args in git_calls)


def test_command_aborts_with_unified_message_when_pr_and_commit_both_fail(
    ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient
) -> None:
    """Pure-digit input: PR 404 (default mock) + commit unresolvable -> unified message."""
    mocker.patch('ddev.utils.git.GitRepository.run')
    mocker.patch('ddev.utils.git.GitRepository.capture', side_effect=OSError('bad object'))
    mocker.patch.dict('os.environ', {'DD_GITHUB_USER': 'alice'})

    result = ddev('release', 'port-commit', '1234567')

    assert result.exit_code == 1, result.output
    assert 'Could not resolve `1234567` as a PR or a commit' in result.output
    assert '`PR-xxxxx`' in result.output


def test_command_aborts_when_commit_log_is_empty(
    ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient
) -> None:
    _setup_command_mocks(mocker)
    mocker.patch('ddev.utils.git.GitRepository.log', return_value=[])
    mocker.patch.dict('os.environ', {'DD_GITHUB_USER': 'alice'})

    result = ddev('release', 'port-commit', '1234567890abcdef00')

    assert result.exit_code == 1, result.output
    assert 'Could not read commit' in result.output
    fake_async_github.assert_not_called('create_pull_request')


def test_command_aborts_on_unconfirmed(
    ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient
) -> None:
    _setup_command_mocks(mocker)
    mocker.patch('click.confirm', return_value=False)
    mocker.patch.dict('os.environ', {'DD_GITHUB_USER': 'alice'})

    result = ddev('release', 'port-commit', '1234567890abcdef00')

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


def test_command_includes_worktree_path_in_dry_run_output(
    ddev: CliRunner, mocker: MockerFixture, fake_async_github: FakeAsyncGitHubClient
) -> None:
    _setup_command_mocks(mocker)
    mocker.patch.dict('os.environ', {'DD_GITHUB_USER': 'alice'})

    result = ddev('release', 'port-commit', '--dry-run', '1234567890abcdef00')

    assert result.exit_code == 0, result.output
    assert StdPath('.worktrees/port-commit/alice-port-1234567890-to-master').as_posix() in result.output.replace(
        '\\', '/'
    )
