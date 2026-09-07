# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re

from semver import VersionInfo

from datadog_checks.dev.fs import chdir
from datadog_checks.dev.subprocess import SubprocessResult, run_command

from .constants import get_root

RELEASE_BRANCH_PATTERN = re.compile(r'^\d+\.\d+\.x$')


def get_git_root():
    """
    Get root of git repo from current location.  Returns 'None' if not in a repo.
    """
    command = 'git rev-parse --show-toplevel'

    result = run_command(command, capture='both')
    if result.stdout:
        return result.stdout.strip()
    elif result.stderr:
        return None


def get_current_branch():
    """
    Get the current branch name.
    """
    command = 'git rev-parse --abbrev-ref HEAD'

    with chdir(get_root()):
        return run_command(command, capture='out').stdout.strip()


def content_changed(file_glob="*"):
    """
    Return the content changed in the current branch compared to `master`
    """
    with chdir(get_root()):
        output = run_command(f'git diff master -U0 -- "{file_glob}"', capture='out')
    return output.stdout


def files_changed(include_uncommitted=True):
    """
    Return the list of file changed in the current branch compared to `master`
    """
    with chdir(get_root()):
        # Use `--name-status` to include moved files
        name_status_result = run_command('git diff --name-status origin/master...', capture='out')

    name_status_lines = name_status_result.stdout.splitlines()

    changed_files = []
    for l in name_status_lines:
        files = l.split('\t')[1:]  # skip first element representing the type of change
        changed_files.extend(files)

    if include_uncommitted:
        with chdir(get_root()):
            # Use `--name-only` to include uncommitted files
            name_only_result = run_command('git diff --name-only master', capture='out')
        name_only_lines = name_only_result.stdout.splitlines()
        changed_files.extend(name_only_lines)

    return sorted([f for f in set(changed_files) if f])


def get_commits_since(check_name, target_tag=None, end=None, exclude_branch=None):
    """
    Get the list of commits from `target_tag` to `HEAD` for the given check
    """
    root = get_root()
    if check_name:
        target_path = os.path.join(root, check_name)
    else:
        target_path = root

    if end is None:
        end = ''

    if exclude_branch is not None and check_name not in {".", None}:
        raise ValueError(f"Cannot exclude a branch from a non-root check {check_name}")
    elif exclude_branch is not None:
        command = f"git cherry -v {exclude_branch} HEAD {'' if target_tag is None else f'{target_tag} '}"
    else:
        command = f"git log --pretty=%s {'' if target_tag is None else f'{target_tag}..{end} '}{target_path}"

    with chdir(root):
        return run_command(command, capture=True, check=True).stdout.splitlines()


def git_show_file(path, ref):
    """
    Return the contents of a file at a given tag
    """
    root = get_root()
    command = f'git show {ref}:{path}'

    with chdir(root):
        return run_command(command, capture=True, check=True).stdout


def git_commit(targets, message, force=False, sign=False, update=False):
    """
    Commit the changes for the given targets.

    `targets` - be files or directories
    `message` - the commit message
    `force` - (optional) force the commit
    `sign` - sign with `-S` option
    `update` - only commit updated files already tracked by git, via `-u`
    """
    root = get_root()
    target_paths = []
    for t in targets:
        target_paths.append(os.path.join(root, t))

    with chdir(root):
        if update:
            result = run_command(f"git add{' -f' if force else ''} -u {' '.join(target_paths)}")
        else:
            result = run_command(f"git add{' -f' if force else ''} {' '.join(target_paths)}")
        if result.code != 0:
            return result

        return run_command('git commit{} -m "{}"'.format(' -S' if sign else '', message))


def git_tag(tag_name, push=False):
    """
    Tag the repo using an annotated tag.
    """
    with chdir(get_root()):
        result = run_command(f'git tag -a {tag_name} -m "{tag_name}"', capture=True)

        if push:
            if result.code != 0:
                return result
            return run_command(f'git push origin {tag_name}', capture=True)

        return result


def git_fetch(remote: str = 'origin', tags: bool = False) -> SubprocessResult:
    """
    Fetch all tags from the remote
    """
    with chdir(get_root()):
        cmd = ['git', 'fetch', remote]
        if tags:
            cmd.append('--tags')
        return run_command(cmd, capture=True)


def git_tag_list(pattern=None, contains=None):
    """
    Return a list of all the tags in the git repo matching a regex passed in
    `pattern`. If `pattern` is None, return all the tags.
    """
    with chdir(get_root()):
        cmd = ['git', 'tag']
        if contains:
            cmd.extend(['--contains', contains])
        result = run_command(cmd, capture=True).stdout
        result = result.splitlines()

    if not pattern:
        return result

    regex = re.compile(pattern)
    return list(filter(regex.search, result))


def get_latest_tag(pattern=None, tag_prefix='v'):
    """
    Return the highest numbered tag (most recent)
    Filters on pattern first, otherwise based off all tags
    Removes prefixed `v` if applicable
    """
    if not pattern:
        pattern = rf'^({tag_prefix})?\d+\.\d+\.\d+.*'
    all_tags = sorted((VersionInfo.parse(t.replace(tag_prefix, '', 1)), t) for t in git_tag_list(pattern))
    if not all_tags:
        return
    else:
        # reverse so we have descending order
        return list(reversed(all_tags))[0][1]


def get_latest_commit_hash(root=None):
    with chdir(root or get_root()):
        result = run_command('git rev-parse HEAD', capture=True, check=True)

    return result.stdout.strip()


def tracked_by_git(filename):
    """
    Return a boolean value for whether the given file is tracked by git.
    """
    with chdir(get_root()):
        # https://stackoverflow.com/a/2406813
        result = run_command(f'git ls-files --error-unmatch {filename}', capture=True)
        return result.code == 0


def ignored_by_git(filename):
    """
    Return a boolean value for whether the given file is ignored by git.
    """
    with chdir(get_root()):
        result = run_command(f'git check-ignore -q {filename}', capture=True)
        return result.code == 0


def get_git_user():
    result = run_command('git config --get user.name', capture=True, check=True)
    return result.stdout.strip()


def get_git_email():
    result = run_command('git config --get user.email', capture=True, check=True)
    return result.stdout.strip()


def get_base_ref() -> str:
    """Return the git ref to compare files against when validating license headers.

    Priority:
    1. GITHUB_BASE_REF (set by GitHub Actions for pull requests — the target branch).
    2. GITHUB_REF_NAME when it is master or a release branch (push events directly to those branches).
    3. Closest ancestor among master and release branches, found via merge-base timestamps.
    """
    github_base_ref = os.environ.get('GITHUB_BASE_REF')
    if github_base_ref:
        return f'origin/{github_base_ref}'

    github_ref_name = os.environ.get('GITHUB_REF_NAME', '')
    if github_ref_name == 'master' or RELEASE_BRANCH_PATTERN.match(github_ref_name):
        return f'origin/{github_ref_name}'

    return _find_closest_base_ref()


def _find_closest_base_ref() -> str:
    """Find the closest ancestor among master and release branches using merge-base timestamps."""
    with chdir(get_root()):
        result = run_command('git for-each-ref --format=%(refname:short) refs/remotes/origin/', capture='out')
        if result.code != 0:
            return 'origin/master'

        candidates = [
            ref
            for ref in result.stdout.strip().splitlines()
            if ref == 'origin/master' or RELEASE_BRANCH_PATTERN.match(ref.removeprefix('origin/'))
        ]

        if not candidates:
            return 'origin/master'

        best_ref = 'origin/master'
        best_timestamp = -1

        for ref in candidates:
            merge_base_result = run_command(f'git merge-base {ref} HEAD', capture='both')
            if merge_base_result.code != 0:
                continue
            merge_base = merge_base_result.stdout.strip()
            if not merge_base:
                continue

            timestamp_result = run_command(f'git show -s --format=%ct {merge_base}', capture='out')
            if timestamp_result.code != 0:
                continue

            try:
                timestamp = int(timestamp_result.stdout.strip())
            except ValueError:
                continue

            if timestamp > best_timestamp:
                best_timestamp = timestamp
                best_ref = ref

        return best_ref
