# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re

from semver import parse_version_info

from ..subprocess import run_command
from ..utils import chdir
from .constants import get_root


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


def files_changed():
    """
    Return the list of file changed in the current branch compared to `master`
    """
    with chdir(get_root()):
        result = run_command('git diff --name-status master...', capture='out')
    status_lines = result.stdout.splitlines()

    changed_files = []
    for l in status_lines:
        files = l.split('\t')[1:]  # skip first element representing the type of change
        changed_files.extend(files)
    return sorted([f for f in changed_files if f])


def get_commits_since(check_name, target_tag=None):
    """
    Get the list of commits from `target_tag` to `HEAD` for the given check
    """
    root = get_root()
    if check_name:
        target_path = os.path.join(root, check_name)
    else:
        target_path = root
    command = f"git log --pretty=%s {'' if target_tag is None else f'{target_tag}... '}{target_path}"

    with chdir(root):
        return run_command(command, capture=True).stdout.splitlines()


def git_show_file(path, ref):
    """
    Return the contents of a file at a given tag
    """
    root = get_root()
    command = f'git show {ref}:{path}'

    with chdir(root):
        return run_command(command, capture=True).stdout


def git_commit(targets, message, force=False, sign=False):
    """
    Commit the changes for the given targets.
    """
    root = get_root()
    target_paths = []
    for t in targets:
        target_paths.append(os.path.join(root, t))

    with chdir(root):
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


def git_tag_list(pattern=None):
    """
    Return a list of all the tags in the git repo matching a regex passed in
    `pattern`. If `pattern` is None, return all the tags.
    """
    with chdir(get_root()):
        result = run_command('git tag', capture=True).stdout
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
    all_tags = sorted(
        (parse_version_info(t.replace(tag_prefix, '', 1)), t) for t in git_tag_list(rf'^({tag_prefix})?\d+\.\d+\.\d+$')
    )
    # reverse so we have descendant order
    return list(reversed(all_tags))[0][1]


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
