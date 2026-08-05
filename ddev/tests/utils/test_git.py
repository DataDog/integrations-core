# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import subprocess
from contextlib import nullcontext

import pytest

from ddev.repo.core import Repository
from ddev.utils.fs import Path
from ddev.utils.git import ChangedFile, ChangeType, parse_name_status
from tests.helpers.git import ClonedRepo


@pytest.fixture(scope="module")
def set_up_repository(local_clone: ClonedRepo):
    repo = Repository(local_clone.path.name, str(local_clone.path))

    repo.git.capture("config", "user.name", "test_user")

    repo.git.capture("checkout", "master")
    (repo.path / "test1.txt").touch()
    repo.git.capture("add", ".")
    repo.git.capture("commit", "-m", "test1")
    (repo.path / "test2.txt").touch()
    repo.git.capture("add", ".")
    repo.git.capture("commit", "-m", "test2")

    repo.git.capture("checkout", "-b", "my-branch")

    (repo.path / "test3.txt").touch()
    repo.git.capture("add", ".")
    repo.git.capture("commit", "-m", "test3")

    repo.git.capture("checkout", "master")

    yield repo
    local_clone.reset_branch()


def test_current_branch(repository):
    repo = Repository(repository.path.name, str(repository.path))

    assert repo.git.current_branch() == repository.testing_branch

    new_branch = repository.new_branch()
    repo.git.capture("checkout", "-b", new_branch)
    assert repo.git.current_branch() == new_branch


def test_get_remote_url_returns_configured_origin(repository):
    repo = Repository(repository.path.name, str(repository.path))

    url = repo.git.get_remote_url('origin')

    assert url is not None
    assert url.strip() == url


def test_get_remote_url_returns_none_when_remote_missing(tmp_path):
    subprocess.run(['git', 'init', '--quiet'], cwd=tmp_path, check=True)
    repo = Repository(tmp_path.name, str(tmp_path))

    assert repo.git.get_remote_url('origin') is None


def test_get_latest_commit(repository):
    repo = Repository(repository.path.name, str(repository.path))

    (repo.path / "test1.txt").touch()
    repo.git.capture("add", ".")
    commit_status1 = repo.git.capture("commit", "-m", "test1")
    commit1 = repo.git.latest_commit()
    assert len(commit1.sha) == 40

    (repo.path / "test2.txt").touch()
    repo.git.capture("add", ".")
    commit_status2 = repo.git.capture("commit", "-m", "test2")
    commit2 = repo.git.latest_commit()
    assert len(commit2.sha) == 40

    short_sha1 = commit1.sha[:7]
    short_sha2 = commit2.sha[:7]

    assert short_sha1 in commit_status1
    assert short_sha1 not in commit_status2
    assert short_sha2 in commit_status2
    assert short_sha2 not in commit_status1


@pytest.mark.parametrize(
    "args, n, source, expected, context",
    [
        (
            ["author:%an", "message:%f"],
            None,
            None,
            [
                {"author": "test_user", "message": "test2"},
                {"author": "test_user", "message": "test1"},
            ],
            nullcontext(),
        ),
        (
            ["author:%an", "message:%f"],
            2,
            None,
            [{"author": "test_user", "message": "test2"}, {"author": "test_user", "message": "test1"}],
            nullcontext(),
        ),
        (
            ["author:%an", "message:%f"],
            0,
            None,
            [],
            nullcontext(),
        ),
        (
            ["author:%an", "message:%f"],
            3,
            "my-branch",
            [
                {"author": "test_user", "message": "test3"},
                {"author": "test_user", "message": "test2"},
                {"author": "test_user", "message": "test1"},
            ],
            nullcontext(),
        ),
        (
            ["%H", "%f"],
            1,
            None,
            None,
            pytest.raises(ValueError),
        ),
    ],
    ids=[
        "test_log_no_n",
        "test_log_two_commits",
        "test_log_zero_commits",
        "test_log_branch_three_commits",
        "test_log_invalid_format_raises",
    ],
)
def test_get_log(set_up_repository, local_clone, config_file, args, n, source, expected, context):
    config_file.model.repos['core'] = str(local_clone.path)
    config_file.save()

    repo = set_up_repository
    kwargs = {}
    if n is not None:
        kwargs['n'] = n
    if source:
        kwargs['source'] = source

    with context:
        if n is None:
            assert len(expected) < len(repo.git.log(args, **kwargs))
        else:
            assert repo.git.log(args, **kwargs) == expected


def test_tags(repository):
    repo = Repository(repository.path.name, str(repository.path))

    assert repo.git.tags() == []

    repo.git.capture("tag", "foo")
    repo.git.capture("tag", "bar")

    assert repo.git.tags() == ["bar", "foo"]


def test_changed_files(repository):
    repo = Repository(repository.path.name, str(repository.path))

    # Committed
    with (repo.path / "pyproject.toml").open(mode="a") as f:
        f.write("\n")

    repo.git.capture("add", "pyproject.toml")
    repo.git.capture("commit", "-m", "test commit")

    # Tracked
    zoo_dir = repo.path / "zoo"
    zoo_dir.mkdir()
    (zoo_dir / "bar.txt").touch()
    repo.git.capture("add", "zoo/bar.txt")

    # Untracked
    zoo_subdir = zoo_dir / "sub"
    zoo_subdir.mkdir()
    (zoo_subdir / "foo.txt").touch()

    changed_files = [
        ChangedFile(ChangeType.ADDED, "zoo/sub/foo.txt"),
        ChangedFile(ChangeType.ADDED, "zoo/bar.txt"),
        ChangedFile(ChangeType.MODIFIED, "pyproject.toml"),
    ]
    assert repo.git.changed_files() == changed_files

    (zoo_subdir / "baz.txt").touch()
    changed_files.insert(0, ChangedFile(ChangeType.ADDED, "zoo/sub/baz.txt"))
    assert repo.git.changed_files() == changed_files


def test_changed_files_between_refs_ignores_the_working_tree(repository):
    repo = Repository(repository.path.name, str(repository.path))

    (repo.path / "committed.txt").touch()
    repo.git.capture("add", "committed.txt")
    repo.git.capture("commit", "-m", "test commit")
    head = repo.git.capture("rev-parse", "HEAD").strip()

    # Uncommitted, so it must not appear when an explicit head is given
    (repo.path / "untracked.txt").touch()

    assert repo.git.changed_files(f"{head}^1", head) == [ChangedFile(ChangeType.ADDED, "committed.txt")]
    assert ChangedFile(ChangeType.ADDED, "untracked.txt") in repo.git.changed_files()


def test_changed_files_reports_renames_with_their_source(repository):
    repo = Repository(repository.path.name, str(repository.path))

    original = repo.path / "renamed_from.txt"
    original.write_text("some content worth detecting as a rename\n" * 10)
    repo.git.capture("add", "renamed_from.txt")
    repo.git.capture("commit", "-m", "add file")
    base = repo.git.capture("rev-parse", "HEAD").strip()

    repo.git.capture("mv", "renamed_from.txt", "renamed_to.txt")
    repo.git.capture("commit", "-m", "rename file")
    head = repo.git.capture("rev-parse", "HEAD").strip()

    assert repo.git.changed_files(base, head) == [
        ChangedFile(ChangeType.RENAMED, "renamed_to.txt", previous_path="renamed_from.txt")
    ]


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        pytest.param("", [], id="empty"),
        pytest.param("A\tadded.py", [ChangedFile(ChangeType.ADDED, "added.py")], id="added"),
        pytest.param("D\tgone.py", [ChangedFile(ChangeType.DELETED, "gone.py")], id="deleted"),
        pytest.param("T\tlink.py", [ChangedFile(ChangeType.MODIFIED, "link.py")], id="type-change-is-a-modification"),
        pytest.param("X\todd.py", [ChangedFile(ChangeType.MODIFIED, "odd.py")], id="unknown-status-is-a-modification"),
        pytest.param(
            "R100\told.py\tnew.py",
            [ChangedFile(ChangeType.RENAMED, "new.py", previous_path="old.py")],
            id="rename-keeps-the-source",
        ),
        pytest.param(
            "C75\tsource.py\tcopy.py",
            [ChangedFile(ChangeType.COPIED, "copy.py", previous_path="source.py")],
            id="copy-keeps-the-source",
        ),
        pytest.param("warning: CRLF\nM\treal.py", [ChangedFile(ChangeType.MODIFIED, "real.py")], id="skips-warnings"),
        pytest.param(
            "M\tpath with spaces.py",
            [ChangedFile(ChangeType.MODIFIED, "path with spaces.py")],
            id="paths-may-contain-spaces",
        ),
    ],
)
def test_parse_name_status(output, expected):
    assert parse_name_status(output) == expected


@pytest.mark.parametrize(
    ("output", "message"),
    [
        pytest.param("M", "Malformed diff line", id="missing-path"),
        pytest.param("R100\tonly_one_path.py", "Malformed rename/copy diff line", id="rename-missing-destination"),
    ],
)
def test_parse_name_status_rejects_malformed_lines(output, message):
    with pytest.raises(ValueError, match=message):
        parse_name_status(output)


def test_filtered_tags(repository):
    repo = Repository(repository.path.name, str(repository.path))

    repo.git.capture("tag", "foo")
    repo.git.capture("tag", "bar")
    repo.git.capture("tag", "baz")

    assert repo.git.filter_tags("^ba") == ["bar", "baz"]


def test_fetch_tags(repository, mocker):
    mock = mocker.patch("subprocess.run")
    repo = Repository(repository.path.name, str(repository.path))
    repo.git.fetch_tags()
    assert mock.call_args_list == [
        mocker.call(
            ["git", "fetch", "--all", "--tags", "--force"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            check=True,
        ),
    ]


def test_get_merge_base(repository):
    repo = Repository(repository.path.name, str(repository.path))
    base_commit = repo.git.latest_commit()
    repo.git.capture('checkout', '-b', 'test_merge_base')

    (repo.path / 'test1.txt').touch()
    repo.git.capture('add', '.')
    repo.git.capture('commit', '-m', 'test1')

    base = repo.git.merge_base('origin/master')

    assert base == base_commit.sha


def test_get_merge_base_two_branches(repository):
    repo = Repository(repository.path.name, str(repository.path))
    base_commit = repo.git.latest_commit()

    repo.git.capture('checkout', '-b', 'test1_merge_base')

    (repo.path / 'test1.txt').touch()
    repo.git.capture('add', '.')
    repo.git.capture('commit', '-m', 'test1')

    repo.git.capture('branch', 'test2_merge_base')

    (repo.path / 'test1_1.txt').touch()
    repo.git.capture('add', '.')
    repo.git.capture('commit', '-m', 'test1_1')

    repo.git.capture('checkout', 'test2_merge_base')
    (repo.path / 'test2_1.txt').touch()
    repo.git.capture('add', '.')
    repo.git.capture('commit', '-m', 'test2')
    base = repo.git.merge_base('origin/master')
    assert base == base_commit.sha


def expected_worktrees(repo: Repository, include_root: bool, only_subpaths: bool) -> list[Path]:
    result = [repo.path / "wt"]

    if include_root:
        result.append(repo.path)
    if not only_subpaths:
        result.append(repo.path.parent / "wt2")

    return result


@pytest.mark.parametrize("include_root", [True, False], ids=["include_root", "exclude_root"])
@pytest.mark.parametrize("only_subpaths", [True, False], ids=["only_subpaths", "not_only_subpaths"])
def test_worktrees(repository: ClonedRepo, include_root: bool, only_subpaths: bool):
    repo = Repository(repository.path.name, str(repository.path))

    worktrees = expected_worktrees(repo, include_root, only_subpaths)

    assert set(repo.git.worktrees(include_root=include_root, only_subpaths=only_subpaths)) == set(worktrees)

    # Add a new worktree
    repo.git.capture("worktree", "add", "t2", "HEAD")
    assert set(repo.git.worktrees(include_root=include_root, only_subpaths=only_subpaths)) == set(
        worktrees + [repo.path / "t2"]
    )

    # Remove it
    repo.git.capture("worktree", "remove", "t2")
    assert set(repo.git.worktrees(include_root=include_root, only_subpaths=only_subpaths)) == set(worktrees)


@pytest.mark.parametrize(
    "include_root, only_subpaths",
    [
        (True, True),
        (True, False),
        (False, True),
        (False, False),
    ],
    ids=[
        "include_root_only_subpaths",
        "include_root_not_only_subpaths",
        "exclude_root_only_subpaths",
        "exclude_root_not_only_subpaths",
    ],
)
def test_is_worktree(
    repository,
    include_root: bool,
    only_subpaths: bool,
):
    repo = Repository(repository.path.name, str(repository.path))

    assert repo.git.is_worktree(repo.path / "wt", include_root=include_root, only_subpaths=only_subpaths)
    assert repo.git.is_worktree(repo.path, include_root=include_root, only_subpaths=only_subpaths) is include_root
    assert (
        repo.git.is_worktree(repo.path.parent / "wt2", include_root=include_root, only_subpaths=only_subpaths)
        is not only_subpaths
    )


def test_worktrees_asks_git_once(repository, mocker):
    repo = Repository(repository.path.name, str(repository.path))
    capture = mocker.spy(repo.git, 'capture')

    for path in repository.path.iterdir():
        repo.git.is_worktree(path)

    assert [call.args for call in capture.call_args_list] == [('worktree', 'list', '--porcelain')]


# Both entry points must invalidate: `capture` is what ddev reads through, `run` is what
# `ddev release port-commit` adds and removes its worktree with.
@pytest.mark.parametrize('entry_point', ['capture', 'run'])
def test_worktrees_are_looked_up_again_after_the_set_changes(repository, entry_point):
    repo = Repository(repository.path.name, str(repository.path))
    git = getattr(repo.git, entry_point)
    added = repo.path / f'wt-{entry_point}'

    assert not repo.git.is_worktree(added)

    # Registering the worktree is enough, and checking out this repository exceeds the Windows
    # path length limit
    git('worktree', 'add', '--no-checkout', str(added), 'HEAD')
    try:
        assert repo.git.is_worktree(added)
    finally:
        # `reset_branch` cannot undo this, so the session-scoped clone would keep the worktree
        git('worktree', 'remove', '--force', str(added))

    assert not repo.git.is_worktree(added)
