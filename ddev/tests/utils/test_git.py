# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import subprocess
from contextlib import nullcontext

import pytest

from ddev.repo.core import Repository
from ddev.utils.fs import Path
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

    changed_files = ["zoo/sub/foo.txt", "zoo/bar.txt", "pyproject.toml"]
    assert repo.git.changed_files() == changed_files

    (zoo_subdir / "baz.txt").touch()
    changed_files.insert(0, "zoo/sub/baz.txt")
    assert repo.git.changed_files() == changed_files


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
