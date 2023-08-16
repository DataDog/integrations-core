# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ddev.repo.core import Repository


def test_current_branch(repository):
    repo = Repository(repository.path.name, str(repository.path))

    assert repo.git.current_branch == repository.testing_branch

    new_branch = repository.new_branch()
    repo.git.capture('checkout', '-b', new_branch)
    assert repo.git.current_branch == repository.testing_branch

    assert repo.git.get_current_branch() == new_branch
    assert repo.git.current_branch == new_branch


def test_get_latest_commit(repository):
    repo = Repository(repository.path.name, str(repository.path))

    (repo.path / 'test1.txt').touch()
    repo.git.capture('add', '.')
    commit_status1 = repo.git.capture('commit', '-m', 'test1')
    commit1 = repo.git.get_latest_commit()
    assert len(commit1.sha) == 40

    (repo.path / 'test2.txt').touch()
    repo.git.capture('add', '.')
    commit_status2 = repo.git.capture('commit', '-m', 'test2')
    commit2 = repo.git.get_latest_commit()
    assert len(commit2.sha) == 40

    short_sha1 = commit1.sha[:7]
    short_sha2 = commit2.sha[:7]

    assert short_sha1 in commit_status1
    assert short_sha1 not in commit_status2
    assert short_sha2 in commit_status2
    assert short_sha2 not in commit_status1


def test_tags(repository):
    repo = Repository(repository.path.name, str(repository.path))

    assert repo.git.tags == []

    repo.git.capture('tag', 'foo')
    repo.git.capture('tag', 'bar')

    assert repo.git.tags == []
    assert repo.git.get_tags() == ['bar', 'foo']
    assert repo.git.tags == ['bar', 'foo']


def test_changed_files(repository):
    repo = Repository(repository.path.name, str(repository.path))

    # Committed
    with (repo.path / 'pyproject.toml').open(mode='a') as f:
        f.write('\n')

    repo.git.capture('add', 'pyproject.toml')
    repo.git.capture('commit', '-m', 'test commit')

    # Tracked
    zoo_dir = repo.path / 'zoo'
    zoo_dir.mkdir()
    (zoo_dir / 'bar.txt').touch()
    repo.git.capture('add', 'zoo/bar.txt')

    # Untracked
    zoo_subdir = zoo_dir / 'sub'
    zoo_subdir.mkdir()
    (zoo_subdir / 'foo.txt').touch()

    changed_files = ['zoo/sub/foo.txt', 'zoo/bar.txt', 'pyproject.toml']
    assert repo.git.changed_files == changed_files

    (zoo_subdir / 'baz.txt').touch()
    assert repo.git.changed_files == changed_files

    changed_files.insert(0, 'zoo/sub/baz.txt')
    assert repo.git.get_changed_files() == changed_files
    assert repo.git.changed_files == changed_files


def test_filtered_tags(repository):
    repo = Repository(repository.path.name, str(repository.path))

    repo.git.capture('tag', 'foo')
    repo.git.capture('tag', 'bar')
    repo.git.capture('tag', 'baz')

    assert repo.git.filter_tags('^ba') == ['bar', 'baz']
