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
