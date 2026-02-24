# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# This file is named with a double underscore so it comes first lexicographically


from ddev.utils.fs import Path
from ddev.utils.git import GitRepository
from tests.helpers import LOCAL_REPO_BRANCH
from tests.helpers.git import ClonedRepo


def commit_from_branch(repository: GitRepository, branch: str) -> str:
    return repository.capture('rev-parse', branch).strip()


def ref_list(repository: GitRepository, left_ref: str, right_ref: str) -> list[str]:
    return repository.capture('rev-list', f"{left_ref}..{right_ref}").strip().splitlines()


def test_cloned_repo(repository: ClonedRepo, local_repo: Path):
    # The cloned repo (repository) should be a repository that is in the LOCAL_REPO_BRANCH
    # branching of from the latest commit in origin master
    # To validate this, we will get the current origin/master updated (in local_repo), check the rev-list
    # between the current branch and origin/master and then validate that this is the same
    # as the rev-list between the repository and local_repo.

    current_repo = GitRepository(local_repo)
    cloned_repo = GitRepository(repository.path)

    current_repo.capture('fetch', 'origin', 'master')
    current_repo_origin_master_ref = commit_from_branch(current_repo, 'origin/master')
    current_repo_head_ref = commit_from_branch(current_repo, "HEAD")

    current_repo_commit_list = ref_list(current_repo, current_repo_origin_master_ref, "HEAD")

    cloned_repo_commit_list = ref_list(cloned_repo, LOCAL_REPO_BRANCH, current_repo_head_ref)

    assert current_repo_commit_list == cloned_repo_commit_list
