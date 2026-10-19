# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import subprocess

import mock
import pytest

from datadog_checks.dev.fs import temp_dir
from datadog_checks.dev.tooling.constants import set_root
from datadog_checks.dev.tooling.git import (
    _find_closest_base_ref,
    files_changed,
    get_base_ref,
    get_commits_since,
    get_current_branch,
    git_commit,
    git_fetch,
    git_show_file,
    git_tag,
    git_tag_list,
    ignored_by_git,
    tracked_by_git,
)


def test_get_current_branch():
    with mock.patch('datadog_checks.dev.tooling.git.chdir') as chdir:
        with mock.patch('datadog_checks.dev.tooling.git.run_command') as run:
            set_root('/foo/')
            get_current_branch()
            chdir.assert_called_once_with('/foo/')
            run.assert_called_once_with('git rev-parse --abbrev-ref HEAD', capture='out')


def test_files_changed():
    with mock.patch('datadog_checks.dev.tooling.git.chdir') as chdir:
        with mock.patch('datadog_checks.dev.tooling.git.run_command') as run:
            name_status_out = mock.MagicMock()
            name_status_out.stdout = '''
M	foo
R100	bar	baz
R100	foo2	foo3
            '''
            name_only_out = mock.MagicMock()
            name_only_out.stdout = '''
file1
file2
'''

            run.side_effect = [name_status_out, name_only_out]
            set_root('/foo/')
            retval = files_changed()

            chdir.assert_has_calls(
                [
                    # since chdir is a context manager, we need to also assert __enter__/__exit__
                    mock.call('/foo/'),
                    mock.call().__enter__(),
                    mock.call().__exit__(None, None, None),
                    mock.call('/foo/'),
                    mock.call().__enter__(),
                    mock.call().__exit__(None, None, None),
                ]
            )
            calls = [
                mock.call('git diff --name-status origin/master...', capture='out'),
                mock.call('git diff --name-only master', capture='out'),
            ]
            run.assert_has_calls(calls)
            assert retval == ['bar', 'baz', 'file1', 'file2', 'foo', 'foo2', 'foo3']


def test_files_changed_not_include_uncommitted():
    with mock.patch('datadog_checks.dev.tooling.git.chdir') as chdir:
        with mock.patch('datadog_checks.dev.tooling.git.run_command') as run:
            name_status_out = mock.MagicMock()
            name_status_out.stdout = '''
M	foo
R100	bar	baz
R100	foo2	foo3
            '''
            run.side_effect = [name_status_out]
            set_root('/foo/')
            retval = files_changed(include_uncommitted=False)

            chdir.assert_called_once_with('/foo/')
            run.assert_called_once_with('git diff --name-status origin/master...', capture='out')
            assert retval == ['bar', 'baz', 'foo', 'foo2', 'foo3']


def test_get_commits_since():
    with mock.patch('datadog_checks.dev.tooling.git.chdir') as chdir:
        with mock.patch('datadog_checks.dev.tooling.git.run_command') as run:
            set_root('/foo/')
            get_commits_since('my-check')
            chdir.assert_called_once_with('/foo/')
            get_commits_since('my-check', target_tag='the-tag')
            run.assert_any_call('git log --pretty=%s /foo/my-check', capture=True, check=True)
            run.assert_any_call('git log --pretty=%s the-tag.. /foo/my-check', capture=True, check=True)


def test_git_show_file():
    with mock.patch('datadog_checks.dev.tooling.git.chdir') as chdir:
        with mock.patch('datadog_checks.dev.tooling.git.run_command') as run:
            set_root('/foo/')
            git_show_file('path-string', 'git-ref-string')
            chdir.assert_called_once_with('/foo/')
            run.assert_called_once_with('git show git-ref-string:path-string', capture=True, check=True)


def test_git_commit():
    with mock.patch('datadog_checks.dev.tooling.git.chdir') as chdir:
        with mock.patch('datadog_checks.dev.tooling.git.run_command') as run:
            set_root('/foo/')
            targets = ['a', 'b', 'c']

            # all good
            run.return_value = mock.MagicMock(code=0)
            git_commit(targets, 'my message')
            chdir.assert_called_once_with('/foo/')
            run.assert_any_call('git add /foo/a /foo/b /foo/c')
            run.assert_any_call('git commit -m "my message"')
            chdir.reset_mock()
            run.reset_mock()

            # all good, more params
            git_commit(targets, 'my message', force=True, sign=True)
            chdir.assert_called_once_with('/foo/')
            run.assert_any_call('git add -f /foo/a /foo/b /foo/c')
            run.assert_any_call('git commit -S -m "my message"')
            chdir.reset_mock()
            run.reset_mock()

            # git add fails
            run.return_value = mock.MagicMock(code=123)
            git_commit(targets, 'my message')
            chdir.assert_called_once_with('/foo/')
            # we expect only one call, git commit should not be called
            run.assert_called_once_with('git add /foo/a /foo/b /foo/c')


def test_git_tag():
    with mock.patch('datadog_checks.dev.tooling.git.chdir') as chdir:
        with mock.patch('datadog_checks.dev.tooling.git.run_command') as run:
            set_root('/foo/')
            run.return_value = mock.MagicMock(code=0)

            # all good
            git_tag('tagname')
            chdir.assert_called_once_with('/foo/')
            run.assert_called_once_with('git tag -a tagname -m "tagname"', capture=True)
            assert run.call_count == 1
            chdir.reset_mock()
            run.reset_mock()

            # again with push
            git_tag('tagname', push=True)
            chdir.assert_called_once_with('/foo/')
            run.assert_any_call('git tag -a tagname -m "tagname"', capture=True)
            run.assert_any_call('git push origin tagname', capture=True)
            chdir.reset_mock()
            run.reset_mock()

            # again with tag failing
            run.return_value = mock.MagicMock(code=123)
            git_tag('tagname', push=True)
            chdir.assert_called_once_with('/foo/')
            # we expect only one call, git push should be skipped
            run.assert_called_once_with('git tag -a tagname -m "tagname"', capture=True)


def test_git_tag_list():
    with mock.patch('datadog_checks.dev.tooling.git.chdir') as chdir:
        with mock.patch('datadog_checks.dev.tooling.git.run_command') as run:
            set_root('/foo/')
            expected = ['a', 'b', 'c']
            run.return_value = mock.MagicMock(code=0)
            run.return_value.stdout = '\n'.join(expected)

            # no pattern
            res = git_tag_list()
            assert res == expected
            chdir.assert_called_once_with('/foo/')
            chdir.reset_mock()
            run.reset_mock()

            # pattern
            res = git_tag_list(r'^a')
            assert res == ['a']
            chdir.assert_called_once_with('/foo/')


def test_ignored_by_git():
    with mock.patch('datadog_checks.dev.tooling.git.chdir') as chdir:
        with mock.patch('datadog_checks.dev.tooling.git.run_command') as run:
            set_root('/foo/')
            ignored_by_git('bar')
            chdir.assert_called_once_with('/foo/')
            run.assert_called_once_with('git check-ignore -q bar', capture=True)


def test_tracked_by_git():
    with mock.patch('datadog_checks.dev.tooling.git.chdir') as chdir:
        with mock.patch('datadog_checks.dev.tooling.git.run_command') as run:
            set_root('/foo/')
            tracked_by_git('bar')
            chdir.assert_called_once_with('/foo/')
            run.assert_called_once_with('git ls-files --error-unmatch bar', capture=True)


@pytest.mark.parametrize(
    'tags, expected_command',
    [
        (True, ['git', 'fetch', 'origin', '--tags']),
        (False, ['git', 'fetch', 'origin']),
    ],
    ids=['with_tags', 'without_tags'],
)
def test_git_fetch(tags: bool, expected_command: list[str]):
    with mock.patch('datadog_checks.dev.tooling.git.chdir') as chdir:
        with mock.patch('datadog_checks.dev.tooling.git.run_command') as run:
            set_root('/foo/')
            git_fetch(tags=tags)
            chdir.assert_called_once_with('/foo/')
            run.assert_called_once_with(expected_command, capture=True)


@pytest.mark.parametrize(
    'github_base_ref, expected',
    [
        ('master', 'origin/master'),
        ('7.80.x', 'origin/7.80.x'),
        ('7.81.x', 'origin/7.81.x'),
    ],
)
def test_get_base_ref_uses_github_base_ref(monkeypatch, github_base_ref, expected):
    monkeypatch.setenv('GITHUB_BASE_REF', github_base_ref)
    monkeypatch.delenv('GITHUB_REF_NAME', raising=False)
    assert get_base_ref() == expected


@pytest.mark.parametrize(
    'github_ref_name, expected',
    [
        ('master', 'origin/master'),
        ('7.80.x', 'origin/7.80.x'),
        ('7.81.x', 'origin/7.81.x'),
    ],
)
def test_get_base_ref_uses_github_ref_name_for_base_branches(monkeypatch, github_ref_name, expected):
    monkeypatch.delenv('GITHUB_BASE_REF', raising=False)
    monkeypatch.setenv('GITHUB_REF_NAME', github_ref_name)
    assert get_base_ref() == expected


@pytest.mark.parametrize(
    'github_ref_name',
    ['aarakke/my-feature', 'feature-branch', ''],
)
def test_get_base_ref_falls_back_to_git_for_feature_branches(monkeypatch, github_ref_name):
    monkeypatch.delenv('GITHUB_BASE_REF', raising=False)
    monkeypatch.setenv('GITHUB_REF_NAME', github_ref_name)

    with mock.patch('datadog_checks.dev.tooling.git._find_closest_base_ref', return_value='origin/master') as finder:
        result = get_base_ref()
        finder.assert_called_once()
        assert result == 'origin/master'


def test_get_base_ref_github_base_ref_takes_priority_over_ref_name(monkeypatch):
    monkeypatch.setenv('GITHUB_BASE_REF', '7.80.x')
    monkeypatch.setenv('GITHUB_REF_NAME', 'master')
    assert get_base_ref() == 'origin/7.80.x'


def _make_run_command_for_base_ref(remote_branches, merge_bases):
    """Build a run_command mock for _find_closest_base_ref.

    remote_branches: list of 'origin/xxx' strings returned by for-each-ref.
    merge_bases: dict mapping ref -> (merge_base_sha, timestamp_str).
    """
    sha_to_timestamp = dict(merge_bases.values())

    def run_command(cmd, capture=None, **kwargs):
        result = mock.MagicMock()
        if 'for-each-ref' in cmd:
            result.code = 0
            result.stdout = '\n'.join(remote_branches)
        elif 'merge-base' in cmd:
            # command is: git merge-base <ref> HEAD
            ref = cmd.split()[-2]
            if ref in merge_bases:
                result.code = 0
                result.stdout = merge_bases[ref][0]
            else:
                result.code = 1
                result.stdout = ''
        elif 'git show' in cmd:
            sha = cmd.split()[-1]
            ts = sha_to_timestamp.get(sha)
            if ts is not None:
                result.code = 0
                result.stdout = ts
            else:
                result.code = 1
                result.stdout = ''
        else:
            result.code = 1
            result.stdout = ''
        return result

    return run_command


def test_find_closest_base_ref_picks_most_recent_merge_base(restore_root):
    remote_branches = ['origin/master', 'origin/7.80.x', 'origin/7.81.x', 'origin/some-feature']
    merge_bases = {
        'origin/master': ('aaa', '1000'),
        'origin/7.80.x': ('bbb', '2000'),
        'origin/7.81.x': ('ccc', '3000'),
    }

    set_root('/foo/')
    with mock.patch('datadog_checks.dev.tooling.git.chdir'):
        with mock.patch(
            'datadog_checks.dev.tooling.git.run_command',
            side_effect=_make_run_command_for_base_ref(remote_branches, merge_bases),
        ):
            assert _find_closest_base_ref() == 'origin/7.81.x'


def test_find_closest_base_ref_returns_master_when_no_candidates(restore_root):
    set_root('/foo/')
    with mock.patch('datadog_checks.dev.tooling.git.chdir'):
        with mock.patch('datadog_checks.dev.tooling.git.run_command') as run:
            run.return_value = mock.MagicMock(code=0, stdout='origin/some-feature\norigin/other')
            assert _find_closest_base_ref() == 'origin/master'


def test_find_closest_base_ref_returns_master_when_for_each_ref_fails(restore_root):
    set_root('/foo/')
    with mock.patch('datadog_checks.dev.tooling.git.chdir'):
        with mock.patch('datadog_checks.dev.tooling.git.run_command') as run:
            run.return_value = mock.MagicMock(code=1, stdout='')
            assert _find_closest_base_ref() == 'origin/master'


def test_find_closest_base_ref_returns_master_when_all_merge_base_calls_fail(restore_root):
    set_root('/foo/')
    with mock.patch('datadog_checks.dev.tooling.git.chdir'):
        with mock.patch(
            'datadog_checks.dev.tooling.git.run_command',
            side_effect=_make_run_command_for_base_ref(['origin/master', 'origin/7.80.x'], {}),
        ):
            assert _find_closest_base_ref() == 'origin/master'


def _git(repo, *args, date=None):
    env = os.environ.copy()
    if date is not None:
        env['GIT_AUTHOR_DATE'] = date
        env['GIT_COMMITTER_DATE'] = date
    subprocess.run(['git', *args], cwd=repo, env=env, check=True, capture_output=True)


@pytest.fixture
def release_branch_repo(restore_root):
    """A real git repo where a feature branch is cut from a release branch.

    History (oldest to newest):
        master (C1) <- 7.80.x (C2) <- 7.81.x (C3) <- feature (C4, HEAD)

    Remote-tracking refs are populated since the finder inspects refs/remotes/origin/.
    `origin/HEAD` and `origin/some-feature` are added to verify non-base refs are ignored.
    """
    with temp_dir() as repo:
        _git(repo, '-c', 'init.defaultBranch=master', 'init')
        _git(repo, 'config', 'user.email', 'test@example.com')
        _git(repo, 'config', 'user.name', 'Test')
        _git(repo, 'commit', '--allow-empty', '-m', 'C1 on master', date='2020-01-01T00:00:00')
        _git(repo, 'checkout', '-b', '7.80.x')
        _git(repo, 'commit', '--allow-empty', '-m', 'C2 on 7.80.x', date='2021-01-01T00:00:00')
        _git(repo, 'checkout', '-b', '7.81.x')
        _git(repo, 'commit', '--allow-empty', '-m', 'C3 on 7.81.x', date='2022-01-01T00:00:00')
        _git(repo, 'checkout', '-b', 'feature')
        _git(repo, 'commit', '--allow-empty', '-m', 'C4 on feature', date='2023-01-01T00:00:00')
        _git(repo, 'update-ref', 'refs/remotes/origin/master', 'master')
        _git(repo, 'update-ref', 'refs/remotes/origin/7.80.x', '7.80.x')
        _git(repo, 'update-ref', 'refs/remotes/origin/7.81.x', '7.81.x')
        _git(repo, 'update-ref', 'refs/remotes/origin/some-feature', 'feature')
        _git(repo, 'symbolic-ref', 'refs/remotes/origin/HEAD', 'refs/remotes/origin/master')
        set_root(repo)
        yield repo


def test_find_closest_base_ref_against_real_repo(release_branch_repo):
    # The feature branch was cut from 7.81.x, so that is the most recent merge base.
    assert _find_closest_base_ref() == 'origin/7.81.x'


def test_get_base_ref_against_real_repo(release_branch_repo, monkeypatch):
    monkeypatch.delenv('GITHUB_BASE_REF', raising=False)
    monkeypatch.delenv('GITHUB_REF_NAME', raising=False)
    assert get_base_ref() == 'origin/7.81.x'


def test_find_closest_base_ref_against_branch_off_master(restore_root):
    """A feature cut from master after a release branch diverged resolves to master."""
    with temp_dir() as repo:
        _git(repo, '-c', 'init.defaultBranch=master', 'init')
        _git(repo, 'config', 'user.email', 'test@example.com')
        _git(repo, 'config', 'user.name', 'Test')
        _git(repo, 'commit', '--allow-empty', '-m', 'C1 on master', date='2020-01-01T00:00:00')
        _git(repo, 'checkout', '-b', '7.80.x')
        _git(repo, 'commit', '--allow-empty', '-m', 'C2 on 7.80.x', date='2021-01-01T00:00:00')
        _git(repo, 'checkout', 'master')
        _git(repo, 'commit', '--allow-empty', '-m', 'C3 on master', date='2022-01-01T00:00:00')
        _git(repo, 'checkout', '-b', 'feature')
        _git(repo, 'commit', '--allow-empty', '-m', 'C4 on feature', date='2023-01-01T00:00:00')
        _git(repo, 'update-ref', 'refs/remotes/origin/master', 'master')
        _git(repo, 'update-ref', 'refs/remotes/origin/7.80.x', '7.80.x')
        set_root(repo)

        # merge-base(feature, master) is C3 (2022), newer than merge-base(feature, 7.80.x) at C1 (2020).
        assert _find_closest_base_ref() == 'origin/master'
